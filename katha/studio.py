import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class StudioError(Exception):
    pass


FINAL_EXPORT_APPROVAL = "final export गर"


def load_project(path):
    path = Path(path).resolve()
    try:
        with path.open(encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError) as exc:
        raise StudioError(f"Cannot read project {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise StudioError("Project must be a JSON object")
    for key, default, low, high in (
        ("width", 1080, 2, 4096), ("height", 1920, 2, 4096),
        ("fps", 30, 1, 60), ("font_size", 64, 8, 300),
    ):
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise StudioError(f"{key} must be an integer between {low} and {high}")
        config[key] = value
    if config["width"] % 2 or config["height"] % 2:
        raise StudioError("width and height must be even for the output pixel format")
    scenes = config.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise StudioError("scenes must be a non-empty array")
    for i, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise StudioError(f"Scene {i} must be an object")
        duration = scene.get("duration")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0 < duration <= 600:
            raise StudioError(f"Scene {i} duration must be greater than 0 and at most 600 seconds")
        if not isinstance(scene.get("text"), str) or not scene["text"].strip():
            raise StudioError(f"Scene {i} needs non-empty text")
        visual = scene.get("visual")
        if not isinstance(visual, dict) or visual.get("type") not in ("color", "stock", "generated", "file"):
            raise StudioError(f"Scene {i} needs a supported visual type")
        kind = visual["type"]
        media = visual.get("media", "image")
        if media not in ("image", "video") or (kind == "color" and media != "image"):
            raise StudioError(f"Scene {i} visual.media must be image or video (color supports image only)")
        if kind == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(visual.get("color", ""))):
            raise StudioError(f"Scene {i} color must be a hex color such as #223344")
        field = {"stock": "query", "generated": "prompt", "file": "path"}.get(kind)
        if field and (not isinstance(visual.get(field), str) or not visual[field].strip()):
            raise StudioError(f"Scene {i} needs visual.{field}")
        if "narration" in scene and (not isinstance(scene["narration"], str) or not scene["narration"].strip()):
            raise StudioError(f"Scene {i} narration must be non-empty text")
    for field in ("font", "output", "voiceover", "caption_font"):
        if field in config and (not isinstance(config[field], str) or not config[field].strip()):
            raise StudioError(f"{field} must be a non-empty path")
    if "narration" in config and (not isinstance(config["narration"], dict) or config["narration"].get("provider") != "edge"):
        raise StudioError("narration.provider must be edge")
    if config.get("narration") and config.get("voiceover"):
        raise StudioError("Use either generated narration or voiceover, not both")
    return path.parent, config


def resolve(root, path):
    return (root / path).resolve()


def asset_path(root, index, kind, media="image"):
    extension = "mp4" if media == "video" else ("jpg" if kind == "stock" else "png")
    return root / "assets" / f"scene-{index:03d}.{extension}"


def request_bytes(url, headers=None, limit=20 * 1024 * 1024):
    try:
        with urlopen(Request(url, headers=headers or {}), timeout=30) as response:
            data = response.read(limit + 1)
            if len(data) > limit:
                raise StudioError(f"Response exceeds {limit} bytes")
            return data
    except (HTTPError, URLError, OSError) as exc:
        raise StudioError(f"Download failed: {exc}") from exc


def fetch(root, config):
    stock = [(i, s) for i, s in enumerate(config["scenes"], 1) if s["visual"]["type"] == "stock"]
    if not stock:
        raise StudioError("No stock scenes configured")
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        raise StudioError("Set PEXELS_API_KEY before fetching stock media")
    directory = root / "assets"
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix="katha-stock-", dir=directory) as temp:
        work = Path(temp)
        for index, scene in stock:
            media = scene["visual"].get("media", "image")
            query = urlencode({"query": scene["visual"]["query"], "orientation": "portrait", "per_page": 1})
            endpoint = "https://api.pexels.com/v1/videos/search?" if media == "video" else "https://api.pexels.com/v1/search?"
            raw = request_bytes(endpoint + query, {"Authorization": key}, 2 * 1024 * 1024)
            try:
                results = json.loads(raw)["videos" if media == "video" else "photos"]
                if not results:
                    raise StudioError(f"No Pexels {'videos' if media == 'video' else 'photos'} found for scene {index}")
                item = results[0]
                if media == "video":
                    files = [f for f in item["video_files"] if f.get("file_type") == "video/mp4"
                             and isinstance(f.get("width"), int) and isinstance(f.get("height"), int)
                             and f["width"] <= 1920 and f["height"] <= 1920 and f.get("quality") != "hls"]
                    if not files:
                        raise StudioError(f"No suitable MP4 for scene {index}")
                    chosen = max(files, key=lambda f: (f["height"] >= f["width"], f["width"] * f["height"]))
                    media_url = chosen["link"]
                    artist, artist_url = item["user"]["name"], item["user"]["url"]
                    hosts = ("videos.pexels.com", "player.vimeo.com")
                else:
                    media_url = item["src"]["large2x"]
                    artist, artist_url = item["photographer"], item["photographer_url"]
                    hosts = ("images.pexels.com",)
                parsed = urlparse(media_url)
                if parsed.scheme != "https" or parsed.hostname not in hosts:
                    raise StudioError(f"Unexpected media URL for scene {index}")
                destination = asset_path(root, index, "stock", media).name
                (work / destination).write_bytes(request_bytes(media_url, limit=100 * 1024 * 1024 if media == "video" else 20 * 1024 * 1024))
                records.append({"scene": index, "query": scene["visual"]["query"], "media": media,
                                "photo_url": item["url"], "photographer": artist, "photographer_url": artist_url,
                                "license": "https://www.pexels.com/license/"})
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                raise StudioError(f"Invalid Pexels response for scene {index}: {exc}") from exc
        for index, scene in stock:
            destination = asset_path(root, index, "stock", scene["visual"].get("media", "image"))
            os.replace(work / destination.name, destination)
        (directory / "provenance.json").write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Downloaded {len(records)} stock asset(s) from https://www.pexels.com/; review assets/provenance.json and rights.")


def run(args, cwd):
    try:
        subprocess.run(args, cwd=str(cwd), check=True)
    except FileNotFoundError as exc:
        raise StudioError(f"Executable not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise StudioError(f"Command failed with exit code {exc.returncode}: {args[0]}") from exc


def generate(root, config):
    scenes = [(i, s) for i, s in enumerate(config["scenes"], 1) if s["visual"]["type"] == "generated"]
    if not scenes:
        raise StudioError("No generated scenes configured")
    generator = config.get("generator")
    command = generator.get("command") if isinstance(generator, dict) else None
    if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
        raise StudioError("generator.command must be a non-empty array of arguments")
    if not any("{output}" in arg for arg in command) or not any("{prompt}" in arg for arg in command):
        raise StudioError("generator.command must contain {prompt} and {output}")
    directory = root / "assets"
    directory.mkdir(parents=True, exist_ok=True)
    for index, scene in scenes:
        if asset_path(root, index, "generated", scene["visual"].get("media", "image")).exists():
            raise StudioError(f"Generated asset already exists for scene {index}; move it before regenerating")
    with tempfile.TemporaryDirectory(prefix="katha-generated-", dir=directory) as temp:
        work = Path(temp)
        for index, scene in scenes:
            destination = work / asset_path(root, index, "generated", scene["visual"].get("media", "image")).name
            args = [arg.replace("{prompt}", scene["visual"]["prompt"]).replace("{output}", str(destination)) for arg in command]
            run(args, root)
            if not destination.is_file() or destination.stat().st_size == 0:
                raise StudioError(f"Generator did not create a visual for scene {index}")
        for index, scene in scenes:
            destination = asset_path(root, index, "generated", scene["visual"].get("media", "image"))
            os.replace(work / destination.name, destination)
    print(f"Generated {len(scenes)} visual(s); review rights, content, and provider charges.")


def audio_duration(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise StudioError("ffprobe is required for timed narration")
    try:
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                                capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("invalid duration")
        return duration
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise StudioError(f"Cannot read narration duration from {path}: {exc}") from exc


def transcribe(source, whisper, model, output, language):
    source = Path(source).resolve()
    model = Path(model).resolve()
    output = Path(output).resolve()
    executable = shutil.which(whisper)
    if not source.is_file():
        raise StudioError(f"Audio or video not found: {source}")
    if not model.is_file():
        raise StudioError(f"Whisper model not found: {model}")
    if not executable:
        raise StudioError(f"Whisper executable not found: {whisper}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise StudioError("FFmpeg not found on PATH")
    if not re.fullmatch(r"[a-z]{2,3}|auto", language):
        raise StudioError("language must be a lowercase language code such as ne, or auto")
    if output.suffix.lower() != ".json":
        raise StudioError("Transcript output must have a .json extension")
    if output in (source, model, Path(executable).resolve()) or output.exists():
        raise StudioError(f"Transcript output already exists or would overwrite an input: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="katha-transcribe-", dir=output.parent) as temp:
        work = Path(temp)
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
             "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(work / "audio.wav")], work)
        run([str(Path(executable).resolve()), "-m", str(model), "-f", str(work / "audio.wav"),
             "-l", language, "-ojf", "-of", str(work / "transcript")], work)
        result = work / "transcript.json"
        try:
            data = json.loads(result.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("transcription"), list):
                raise ValueError("missing transcription array")
        except (OSError, ValueError) as exc:
            raise StudioError(f"Whisper did not produce valid full JSON: {exc}") from exc
        try:
            with output.open("xb") as destination, result.open("rb") as draft:
                shutil.copyfileobj(draft, destination)
        except FileExistsError as exc:
            raise StudioError(f"Transcript output already exists: {output}") from exc
    print(f"Transcript saved to {output}. Text and timings are unverified and must not be used as final captions.")


def validate_video(path, index):
    try:
        result = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-select_streams", "v:0",
                                 "-show_entries", "stream=codec_type,width,height:format=duration",
                                 "-of", "json", str(path)],
                                capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        streams = metadata["streams"]
        duration = float(metadata["format"]["duration"])
        if not streams or not streams[0].get("width") or not streams[0].get("height") or not math.isfinite(duration) or duration <= 0:
            raise ValueError("no video stream")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        raise StudioError(f"Scene {index} is not a readable video: {path}") from exc


def validate_render(path, config, expected_duration):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise StudioError("FFmpeg and ffprobe are required to validate the rendered video")
    try:
        result = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                                capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        streams = metadata["streams"]
        video = [stream for stream in streams if stream.get("codec_type") == "video"]
        audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
        duration = float(metadata["format"]["duration"])
        if len(video) != 1:
            raise ValueError("expected exactly one video stream")
        if (video[0].get("width"), video[0].get("height")) != (config["width"], config["height"]):
            raise ValueError("rendered dimensions do not match the project")
        rate = video[0].get("avg_frame_rate", "0/1").split("/")
        if len(rate) != 2 or float(rate[1]) == 0 or abs(float(rate[0]) / float(rate[1]) - config["fps"]) > 0.01:
            raise ValueError("rendered frame rate does not match the project")
        if bool(audio) != bool(config.get("voiceover") or config.get("narration")):
            raise ValueError("rendered audio streams do not match the project")
        if not math.isfinite(duration) or abs(duration - expected_duration) > max(0.15, 2 / config["fps"]):
            raise ValueError("rendered duration does not match the project")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        raise StudioError(f"Rendered video failed output validation: {exc}") from exc
    try:
        result = subprocess.run([ffmpeg, "-hide_banner", "-v", "error", "-i", str(path), "-f", "null", "-"],
                                capture_output=True, text=True, check=True)
        if result.stderr.strip():
            raise ValueError(result.stderr.strip())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise StudioError(f"Rendered video cannot be decoded cleanly: {exc}") from exc


def prepare(root, config):
    scenes = config["scenes"]
    for index, scene in enumerate(scenes, 1):
        visual = scene["visual"]
        if visual.get("media") != "video" or visual["type"] not in ("stock", "generated", "file"):
            raise StudioError(f"Scene {index} needs moving video; prepare does not substitute a slideshow")
        if visual["type"] == "file" and not resolve(root, visual["path"]).is_file():
            raise StudioError(f"Scene {index} video not found: {visual['path']}")
    kinds = {scene["visual"]["type"] for scene in scenes}
    if "stock" in kinds and not os.environ.get("PEXELS_API_KEY"):
        raise StudioError("Set PEXELS_API_KEY before preparing stock scenes")
    if "generated" in kinds:
        generator = config.get("generator")
        command = generator.get("command") if isinstance(generator, dict) else None
        if (not isinstance(command, list) or not command or
                any(not isinstance(arg, str) or not arg for arg in command) or
                not any("{prompt}" in arg for arg in command) or
                not any("{output}" in arg for arg in command)):
            raise StudioError("generator.command must be an argument list containing {prompt} and {output}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise StudioError("FFmpeg and ffprobe are required for preparation")
    if not config.get("font") or not resolve(root, config["font"]).is_file():
        raise StudioError("Set font to an existing font file")
    if config.get("narration"):
        voice = config["narration"].get("voice", "ne-NP-HemkalaNeural")
        if not isinstance(voice, str) or not voice.strip():
            raise StudioError("narration.voice must be a non-empty voice name")
        if importlib.util.find_spec("edge_tts") is None:
            raise StudioError("Install optional speech dependencies: pip install -r requirements-voice.txt")
    for index, scene in enumerate(scenes, 1):
        if scene["visual"]["type"] == "file":
            validate_video(resolve(root, scene["visual"]["path"]), index)
    assets = root / "assets"
    targets = [asset_path(root, i, scene["visual"]["type"], "video")
               for i, scene in enumerate(scenes, 1) if scene["visual"]["type"] in ("stock", "generated")]
    if "stock" in kinds:
        targets.append(assets / "provenance.json")
    if config.get("narration"):
        targets.extend([assets / "narration.json"] +
                       [assets / f"voice-{i:03d}.mp3" for i in range(1, len(scenes) + 1)])
    if any(path.exists() for path in targets):
        raise StudioError("Preparation would overwrite existing assets; use a fresh project directory")

    storyboard = [{"scene": i, "duration": scene["duration"], "narration": scene.get("narration", scene["text"]),
                   "visual": scene["visual"]} for i, scene in enumerate(scenes, 1)]
    print("Scene plan (not a complete storyboard; final timing may change with narration):")
    print(json.dumps(storyboard, ensure_ascii=False, indent=2), flush=True)
    if "stock" in kinds:
        fetch(root, config)
    if "generated" in kinds:
        generate(root, config)
    for index, scene in enumerate(scenes, 1):
        visual = scene["visual"]
        path = resolve(root, visual["path"]) if visual["type"] == "file" else asset_path(root, index, visual["type"], "video")
        validate_video(path, index)
    if config.get("narration"):
        from .speech import narrate
        narrate(root, config)
    print("Preparation complete; no video was rendered. Technical checks cannot verify visual quality or factual accuracy.")


def render(root, config, approval=None):
    if approval != FINAL_EXPORT_APPROVAL:
        raise StudioError(f'Final rendering requires explicit approval: "{FINAL_EXPORT_APPROVAL}"')
    font = config.get("font")
    if not font or not resolve(root, font).is_file():
        raise StudioError("Set font to an existing font file")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise StudioError("FFmpeg not found on PATH")
    voice = resolve(root, config["voiceover"]) if config.get("voiceover") else None
    if voice and not voice.is_file():
        raise StudioError(f"Voiceover not found: {voice}")
    output = resolve(root, config.get("output", "output/video.mp4"))
    if output.suffix.lower() != ".mp4":
        raise StudioError("output must be an .mp4 path")
    if output == voice:
        raise StudioError("output must not overwrite the voiceover")
    width, height, fps = config["width"], config["height"], config["fps"]
    narration_records = None
    if config.get("narration"):
        try:
            narration_records = json.loads((root / "assets" / "narration.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StudioError("Narration metadata is missing or invalid; run narrate first") from exc
        if not isinstance(narration_records, list) or len(narration_records) != len(config["scenes"]):
            raise StudioError("Narration metadata does not match the project; run narrate again")
    stock_records = None
    if any(scene["visual"]["type"] == "stock" for scene in config["scenes"]):
        try:
            stock_records = json.loads((root / "assets" / "provenance.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StudioError("Stock provenance is missing or invalid; fetch stock again") from exc
        if not isinstance(stock_records, list):
            raise StudioError("Stock provenance is invalid; fetch stock again")
    for index, scene in enumerate(config["scenes"], 1):
        visual = scene["visual"]
        if visual["type"] != "color":
            media = visual.get("media", "image")
            source = resolve(root, visual["path"]) if visual["type"] == "file" else asset_path(root, index, visual["type"], media)
            if not source.is_file():
                raise StudioError(f"Scene {index} visual not found: {source}; fetch or generate it first")
            if source == output:
                raise StudioError("output must not overwrite a source image")
            if visual["type"] == "stock" and not any(
                isinstance(record, dict) and record.get("scene") == index and record.get("query") == visual["query"]
                and record.get("media", "image") == media
                for record in stock_records
            ):
                raise StudioError(f"Stock provenance does not match scene {index}; fetch stock again")
        if narration_records is not None:
            record = narration_records[index - 1]
            audio = root / "assets" / f"voice-{index:03d}.mp3"
            if not isinstance(record, dict) or record.get("scene") != index or record.get("text") != scene.get("narration", scene["text"]) or record.get("voice") != config["narration"].get("voice", "ne-NP-HemkalaNeural") or not audio.is_file():
                raise StudioError(f"Narration does not match scene {index}; run narrate again")
    output.parent.mkdir(parents=True, exist_ok=True)
    expected_duration = sum(
        max(scene["duration"], audio_duration(root / "assets" / f"voice-{index:03d}.mp3") + 0.2)
        if narration_records is not None else scene["duration"]
        for index, scene in enumerate(config["scenes"], 1)
    )
    with tempfile.TemporaryDirectory(prefix="katha-", dir=output.parent) as temp:
        work = Path(temp)
        shutil.copyfile(resolve(root, font), work / "font")
        if narration_records is not None:
            from .speech import captions_ass
            shutil.copyfile(resolve(root, font), work / ("caption-font" + resolve(root, font).suffix))
        for index, scene in enumerate(config["scenes"], 1):
            visual = scene["visual"]
            caption = "\n".join(textwrap.wrap(scene["text"], width=max(10, width // max(config["font_size"] // 2, 1)),
                                              break_long_words=False, break_on_hyphens=False))
            (work / "caption.txt").write_text(caption, encoding="utf-8")
            args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
            if visual["type"] == "color":
                args += ["-f", "lavfi", "-i", f"color=c=0x{visual['color'][1:]}:s={width}x{height}:r={fps}"]
            else:
                media = visual.get("media", "image")
                source = resolve(root, visual["path"]) if visual["type"] == "file" else asset_path(root, index, visual["type"], media)
                args += (["-stream_loop", "-1"] if media == "video" else ["-loop", "1", "-framerate", str(fps)]) + ["-i", str(source)]
            duration = scene["duration"]
            vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
            if narration_records is not None:
                audio = root / "assets" / f"voice-{index:03d}.mp3"
                duration = max(duration, audio_duration(audio) + 0.2)
                args += ["-i", str(audio)]
                (work / "captions.ass").write_text(
                    captions_ass(narration_records[index - 1].get("words"), width, height, config["font_size"],
                                 config.get("caption_font", "Nirmala UI")), encoding="utf-8")
                vf += "ass=captions.ass:fontsdir=."
                args += ["-map", "0:v:0", "-map", "1:a:0", "-af", "apad", "-c:a", "aac"]
            else:
                vf += (f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.35:t=fill,"
                       f"drawtext=fontfile=font:textfile=caption.txt:expansion=none:"
                       f"fontcolor=white:fontsize={config['font_size']}:line_spacing=12:"
                       "x=(w-text_w)/2:y=(h-text_h)/2")
                args += ["-an"]
            args += ["-t", str(duration), "-vf", vf, "-r", str(fps),
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", f"scene-{index:03d}.mp4"]
            run(args, work)
        (work / "concat.txt").write_text("".join(f"file 'scene-{i:03d}.mp4'\n" for i in range(1, len(config["scenes"]) + 1)), encoding="utf-8")
        run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "1",
             "-i", "concat.txt", "-c", "copy", "joined.mp4"], work)
        args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", "joined.mp4"]
        if voice:
            args += ["-i", str(voice), "-filter_complex", "[1:a]apad[a]", "-map", "0:v:0", "-map", "[a]",
                     "-c:v", "copy", "-c:a", "aac", "-shortest"]
        else:
            args += ["-c", "copy"]
        args += ["final.mp4"]
        run(args, work)
        validate_render(work / "final.mp4", config, expected_duration)
        os.replace(work / "final.mp4", output)
    print(f"Rendered {output}. Review before publishing.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Produce a reviewable vertical video from a JSON project.")
    parser.add_argument("command", choices=("fetch", "generate", "narrate", "prepare", "reel", "render", "transcribe"))
    parser.add_argument("project", help="Project JSON, or audio/video input for transcribe")
    parser.add_argument("--whisper", help="Path to whisper-cli executable (transcribe)")
    parser.add_argument("--model", help="Path to multilingual whisper.cpp model (transcribe)")
    parser.add_argument("--output", help="Transcript JSON path (transcribe)")
    parser.add_argument("--language", default="ne", help="Whisper language code or auto (default: ne)")
    parser.add_argument("--approval", help="Explicit final-export approval (render)")
    args = parser.parse_args(argv)
    try:
        if args.command == "transcribe":
            if not args.whisper or not args.model:
                raise StudioError("transcribe requires --whisper and --model")
            output = args.output or str(Path("transcripts") / (Path(args.project).stem + ".json"))
            transcribe(args.project, args.whisper, args.model, output, args.language)
            return 0
        if args.command == "reel":
            from .reel import reel
            return reel(args.project, approval=args.approval)
        if args.command == "render" and args.approval != FINAL_EXPORT_APPROVAL:
            raise StudioError('Show a storyboard first; render only after approval with --approval "final export गर"')
        root, config = load_project(args.project)
        if args.command == "narrate":
            from .speech import narrate
            narrate(root, config)
        else:
            if args.command == "render":
                render(root, config, approval=args.approval)
            else:
                {"fetch": fetch, "generate": generate, "prepare": prepare}[args.command](root, config)
        return 0
    except (StudioError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

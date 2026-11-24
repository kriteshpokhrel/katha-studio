import asyncio
import json
import math
import os
from pathlib import Path
import tempfile
import unicodedata

from .studio import StudioError, audio_duration


def spoken_text_key(value):
    return "".join(char for char in unicodedata.normalize("NFC", value).casefold()
                   if unicodedata.category(char)[0] in ("L", "M", "N"))


async def synthesize(text, voice, path):
    try:
        import edge_tts
        import aiohttp
    except ImportError as exc:
        raise StudioError("Install optional speech dependencies: pip install -r requirements-voice.txt") from exc
    words = []
    try:
        with path.open("wb") as audio:
            speech = edge_tts.Communicate(text, voice, boundary="WordBoundary")
            async for chunk in speech.stream():
                if chunk["type"] == "audio":
                    audio.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append({"text": chunk["text"], "start": chunk["offset"] / 10_000_000,
                                  "end": (chunk["offset"] + chunk["duration"]) / 10_000_000})
    except (edge_tts.exceptions.EdgeTTSException, aiohttp.ClientError, OSError, asyncio.TimeoutError, ValueError) as exc:
        raise StudioError(f"Speech synthesis failed: {exc}") from exc
    if not path.stat().st_size or not words:
        raise StudioError("Speech provider returned no audio or word timestamps")
    return words


def narrate(root, config):
    settings = config.get("narration")
    if not isinstance(settings, dict) or settings.get("provider") != "edge":
        raise StudioError("Set narration.provider to edge before generating narration")
    voice = settings.get("voice", "ne-NP-HemkalaNeural")
    if not isinstance(voice, str) or not voice.strip():
        raise StudioError("narration.voice must be a non-empty voice name")
    directory = root / "assets"
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="katha-voice-", dir=directory) as temp:
        work = Path(temp)
        records = []
        for index, scene in enumerate(config["scenes"], 1):
            text = scene.get("narration", scene["text"])
            if not isinstance(text, str) or not text.strip():
                raise StudioError(f"Scene {index} narration must be non-empty text")
            path = work / f"voice-{index:03d}.mp3"
            words = asyncio.run(synthesize(text, voice, path))
            captions_ass(words, config["width"], config["height"], config["font_size"],
                         config.get("caption_font", "Nirmala UI"))
            if spoken_text_key(text) != spoken_text_key("".join(word["text"] for word in words)):
                raise StudioError(f"Speech word boundaries do not match scene {index} narration")
            if words[-1]["end"] > audio_duration(path) + 0.1:
                raise StudioError(f"Speech word timestamps exceed scene {index} audio duration")
            records.append({"scene": index, "text": text, "voice": voice, "words": words})
        (work / "narration.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for index in range(1, len(records) + 1):
            os.replace(work / f"voice-{index:03d}.mp3", directory / f"voice-{index:03d}.mp3")
        os.replace(work / "narration.json", directory / "narration.json")
    print("Narration generated. Pronunciation, provider terms and charges still require verification.")


def ass_time(seconds):
    centiseconds = max(0, round(seconds * 100))
    return f"{centiseconds // 360000}:{centiseconds // 6000 % 60:02}:{centiseconds // 100 % 60:02}.{centiseconds % 100:02}"


def escape_ass(text):
    return text.replace("\\", "\\\\").replace("{", "").replace("}", "").replace("\n", " ")


def captions_ass(words, width, height, size, font_name):
    if not isinstance(words, list) or not words:
        raise StudioError("Narration has no word timestamps")
    if any(not isinstance(word, dict) or not isinstance(word.get("text"), str)
           or not isinstance(word.get("start"), (int, float)) or not isinstance(word.get("end"), (int, float))
           or not math.isfinite(word["start"]) or not math.isfinite(word["end"])
           or not 0 <= word["start"] < word["end"] for word in words):
        raise StudioError("Narration word timestamps are invalid")
    if any(words[i]["start"] >= words[i + 1]["start"] for i in range(len(words) - 1)):
        raise StudioError("Narration word timestamps must be ordered")
    if any(c in font_name for c in ",\r\n"):
        raise StudioError("caption_font cannot contain commas or newlines")
    header = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 2\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Caption,{font_name},{size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{max(2, size // 18)},2,2,{width // 12},{width // 12},{height // 5},1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    max_chars = max(10, int((width * 851 / 1080) / (size * 0.75)))
    groups = []
    for word in words:
        if not groups or len(groups[-1]) >= 3 or sum(len(w["text"]) for w in groups[-1]) + len(word["text"]) + len(groups[-1]) > max_chars:
            groups.append([])
        groups[-1].append(word)
    events = []
    for group in groups:
        for index, word in enumerate(group):
            end = group[index + 1]["start"] if index + 1 < len(group) else word["end"]
            parts = []
            for position, item in enumerate(group):
                color = r"{\c&H00FFFF&}" if position == index else r"{\c&HFFFFFF&}"
                parts.append(color + escape_ass(item["text"]))
            position = rf"{{\pos({round(width * 490.5 / 1080)},{round(height * 1240 / 1920)})}}"
            events.append(f"Dialogue: 0,{ass_time(word['start'])},{ass_time(end)},Caption,,0,0,0,,{position}{' '.join(parts)}")
    return header + "\n".join(events) + "\n"

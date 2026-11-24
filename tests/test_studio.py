import json
import os
from pathlib import Path
import base64
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from katha import studio
from katha import speech


FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
]
FONT = next((path for path in FONT_CANDIDATES if path.is_file()), None)
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.project = {
            "width": 160, "height": 240, "fps": 10, "font_size": 16,
            "font": str(FONT), "output": "output/test.mp4",
            "scenes": [
                {"duration": 0.6, "text": "Original 100% story", "visual": {"type": "color", "color": "#223344"}},
                {"duration": 0.6, "text": "Second scene", "visual": {"type": "color", "color": "#49353B"}},
            ],
        }

    def load(self):
        path = self.root / "project.json"
        path.write_text(json.dumps(self.project), encoding="utf-8")
        return studio.load_project(path)

    def test_invalid_configuration(self):
        for field, value in (("width", 101), ("fps", 0), ("scenes", [])):
            with self.subTest(field=field):
                old = self.project[field]
                self.project[field] = value
                with self.assertRaises(studio.StudioError):
                    self.load()
                self.project[field] = old
        self.project["scenes"][0]["duration"] = float("nan")
        with self.assertRaises(studio.StudioError):
            self.load()

    def test_missing_dependencies_and_assets(self):
        root, config = self.load()
        config["font"] = "missing.ttf"
        with self.assertRaisesRegex(studio.StudioError, "font"):
            studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)
        config["scenes"][0]["visual"] = {"type": "stock", "query": "mountain"}
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(studio.StudioError, "PEXELS_API_KEY"):
                studio.fetch(root, config)
        config["scenes"][0]["visual"] = {"type": "generated", "prompt": "mountain"}
        with self.assertRaisesRegex(studio.StudioError, "generator.command"):
            studio.generate(root, config)

    def test_stock_fetch_records_attribution_and_rejects_empty_results(self):
        self.project["scenes"][0]["visual"] = {"type": "stock", "query": "mountain"}
        root, config = self.load()
        payload = {"photos": [{"src": {"large2x": "https://images.pexels.com/photo.jpg"},
                              "url": "https://www.pexels.com/photo/1/",
                              "photographer": "Photographer", "photographer_url": "https://www.pexels.com/@photographer"}]}
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test-key"}), \
             patch.object(studio, "request_bytes", side_effect=[json.dumps(payload).encode(), b"photo"]):
            studio.fetch(root, config)
        self.assertEqual(studio.asset_path(root, 1, "stock").read_bytes(), b"photo")
        provenance = json.loads((root / "assets" / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance[0]["photographer"], "Photographer")
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test-key"}), \
             patch.object(studio, "request_bytes", return_value=b'{"photos": []}'):
            with self.assertRaisesRegex(studio.StudioError, "No Pexels photos"):
                studio.fetch(root, config)
        self.assertEqual(studio.asset_path(root, 1, "stock").read_bytes(), b"photo")

    def test_generated_adapter(self):
        self.project["scenes"][0]["visual"] = {"type": "generated", "prompt": "safe prompt"}
        self.project["generator"] = {"command": [sys.executable, "-c",
            "import pathlib,sys; pathlib.Path(sys.argv[2]).write_text(sys.argv[1])", "{prompt}", "{output}"]}
        root, config = self.load()
        studio.generate(root, config)
        self.assertEqual(studio.asset_path(root, 1, "generated").read_text(), "safe prompt")
        with self.assertRaisesRegex(studio.StudioError, "already exists"):
            studio.generate(root, config)

    def test_timed_caption_groups_and_validation(self):
        words = [{"text": "first", "start": 0.1, "end": 0.4},
                 {"text": "second", "start": 0.5, "end": 0.9}]
        captions = speech.captions_ass(words, 720, 1280, 40, "Arial")
        self.assertIn(r"{\c&H00FFFF&}first {\c&HFFFFFF&}second", captions)
        self.assertIn(r"{\c&HFFFFFF&}first {\c&H00FFFF&}second", captions)
        self.assertIn("0:00:00.10,0:00:00.50", captions)
        with self.assertRaisesRegex(studio.StudioError, "timestamps"):
            speech.captions_ass([{"text": "bad", "start": 1, "end": 0}], 720, 1280, 40, "Arial")
        self.assertIn(r"{\pos(327,827)}", captions)

    def test_render_requires_explicit_approval(self):
        project = self.root / "project.json"
        project.write_text(json.dumps(self.project), encoding="utf-8")
        with patch.object(studio, "render") as render:
            self.assertEqual(studio.main(["render", str(project)]), 1)
            self.assertEqual(studio.main(["render", str(project), "--approval", "yes"]), 1)
            render.assert_not_called()
            self.assertEqual(studio.main(["render", str(project), "--approval", studio.FINAL_EXPORT_APPROVAL]), 0)
            render.assert_called_once_with(unittest.mock.ANY, unittest.mock.ANY,
                                           approval=studio.FINAL_EXPORT_APPROVAL)

    def test_prepare_rejects_slides_and_missing_key_before_processing(self):
        root, config = self.load()
        with patch.object(studio, "fetch") as fetch, patch.object(studio, "generate") as generate:
            with self.assertRaisesRegex(studio.StudioError, "moving video"):
                studio.prepare(root, config)
            config["scenes"][0]["visual"] = {"type": "stock", "media": "video", "query": "city"}
            config["scenes"][1]["visual"] = {"type": "stock", "media": "video", "query": "street"}
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(studio.StudioError, "PEXELS_API_KEY"):
                    studio.prepare(root, config)
            fetch.assert_not_called()
            generate.assert_not_called()

    @unittest.skipUnless(FFMPEG and FFPROBE and FONT, "FFmpeg, ffprobe and a test font are required")
    def test_prepare_narrates_video_without_final_render_and_rejects_mismatches(self):
        source = self.root / "moving.mp4"
        audio = self.root / "voice.mp3"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc2=s=160x240:r=10:d=1", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", str(source)], check=True)
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=1", str(audio)], check=True)
        self.project["scenes"] = [{"duration": 1, "text": "one two",
                                   "visual": {"type": "file", "media": "video", "path": str(source)}}]
        self.project["narration"] = {"provider": "edge", "voice": "test"}
        root, config = self.load()

        async def synthesize(text, voice, path):
            shutil.copyfile(audio, path)
            return [{"text": "one", "start": 0.1, "end": 0.4},
                    {"text": "two", "start": 0.5, "end": 0.9}]

        with patch.object(speech, "synthesize", side_effect=synthesize), \
             patch.object(studio.importlib.util, "find_spec", return_value=True):
            studio.prepare(root, config)
        self.assertTrue((root / "assets" / "narration.json").is_file())
        self.assertFalse((root / "output" / "test.mp4").exists())
        with patch.object(studio.importlib.util, "find_spec", return_value=True):
            with self.assertRaisesRegex(studio.StudioError, "overwrite"):
                studio.prepare(root, config)

        config["scenes"][0]["text"] = "different words"
        with patch.object(speech, "synthesize", side_effect=synthesize):
            with self.assertRaisesRegex(studio.StudioError, "do not match"):
                speech.narrate(root, config)
        saved = json.loads((root / "assets" / "narration.json").read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["text"], "one two")

    def test_transcribe_converts_audio_and_preserves_existing_output(self):
        source, model = self.root / "source.mp3", self.root / "model.bin"
        source.write_bytes(b"audio")
        model.write_bytes(b"model")
        output = self.root / "transcripts" / "draft.json"

        def fake_run(args, cwd):
            if "-ojf" in args:
                (cwd / "transcript.json").write_text('{"transcription": []}', encoding="utf-8")

        with patch.object(studio.shutil, "which", side_effect=lambda name: sys.executable), \
             patch.object(studio, "run", side_effect=fake_run) as runner:
            studio.transcribe(source, "whisper", model, output, "ne")
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"transcription": []})
            self.assertIn("16000", runner.call_args_list[0].args[0])
            self.assertIn("-ojf", runner.call_args_list[1].args[0])
            with self.assertRaisesRegex(studio.StudioError, "already exists"):
                studio.transcribe(source, "whisper", model, output, "ne")
            self.assertEqual(runner.call_count, 2)

    def test_transcribe_rejects_missing_model_and_invalid_output(self):
        source = self.root / "source.mp3"
        source.write_bytes(b"audio")
        with self.assertRaisesRegex(studio.StudioError, "model not found"):
            studio.transcribe(source, "whisper", self.root / "missing", self.root / "draft.json", "ne")
        model = self.root / "model.bin"
        model.write_bytes(b"model")
        with patch.object(studio.shutil, "which", return_value=sys.executable):
            with self.assertRaisesRegex(studio.StudioError, "language"):
                studio.transcribe(source, "whisper", model, self.root / "draft.json", "../ne")
            with self.assertRaisesRegex(studio.StudioError, "json extension"):
                studio.transcribe(source, "whisper", model, self.root / "draft.txt", "ne")

    def test_stock_video_download_and_provenance(self):
        self.project["scenes"][0]["visual"] = {"type": "stock", "query": "city", "media": "video"}
        root, config = self.load()
        payload = {"videos": [{"url": "https://www.pexels.com/video/example/",
                               "user": {"name": "Artist", "url": "https://www.pexels.com/@artist"},
                               "video_files": [{"file_type": "video/mp4", "width": 720, "height": 1280,
                                                "quality": "hd", "link": "https://videos.pexels.com/video-files/1/video.mp4"}]}]}
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test-key"}), \
             patch.object(studio, "request_bytes", side_effect=[json.dumps(payload).encode(), b"video"]) as request:
            studio.fetch(root, config)
        self.assertIn("/v1/videos/search?", request.call_args_list[0].args[0])
        self.assertEqual(studio.asset_path(root, 1, "stock", "video").read_bytes(), b"video")
        provenance = json.loads((root / "assets" / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance[0]["media"], "video")

    @unittest.skipUnless(FFMPEG and FFPROBE and FONT, "FFmpeg, ffprobe and a test font are required")
    def test_render_without_media_and_with_optional_voice(self):
        root, config = self.load()
        studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)
        output = root / "output" / "test.mp4"
        probe = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
                               capture_output=True, text=True, check=True)
        result = json.loads(probe.stdout)
        self.assertEqual([stream["codec_type"] for stream in result["streams"]], ["video"])
        self.assertEqual((result["streams"][0]["width"], result["streams"][0]["height"]), (160, 240))
        self.assertAlmostEqual(float(result["format"]["duration"]), 1.2, delta=0.15)
        voice = root / "voice.wav"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=0.2", str(voice)], check=True)
        config["voiceover"] = str(voice)
        studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)
        probe = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
                               capture_output=True, text=True, check=True)
        result = json.loads(probe.stdout)
        self.assertEqual([stream["codec_type"] for stream in result["streams"]], ["video", "audio"])
        self.assertAlmostEqual(float(result["format"]["duration"]), 1.2, delta=0.2)

    @unittest.skipUnless(FFMPEG and FFPROBE and FONT, "FFmpeg, ffprobe and a test font are required")
    def test_stock_and_generated_images_render_and_stock_query_is_checked(self):
        image = self.root / "source.png"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "color=red:s=64x64", "-frames:v", "1", str(image)], check=True)
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        self.project["scenes"][0]["visual"] = {"type": "stock", "query": "mountain"}
        self.project["scenes"][1]["visual"] = {"type": "generated", "prompt": "landscape"}
        self.project["generator"] = {"command": [sys.executable, "-c",
            "import base64,pathlib,sys; pathlib.Path(sys.argv[2]).write_bytes(base64.b64decode(sys.argv[1]))",
            encoded, "{output}", "{prompt}"]}
        root, config = self.load()
        payload = {"photos": [{"src": {"large2x": "https://images.pexels.com/photo.jpg"},
                              "url": "https://www.pexels.com/photo/1/", "photographer": "Artist",
                              "photographer_url": "https://www.pexels.com/@artist"}]}
        with patch.dict(os.environ, {"PEXELS_API_KEY": "test-key"}), \
             patch.object(studio, "request_bytes", side_effect=[json.dumps(payload).encode(), image.read_bytes()]):
            studio.fetch(root, config)
        studio.generate(root, config)
        studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)
        self.assertTrue((root / "output" / "test.mp4").is_file())
        config["scenes"][0]["visual"]["query"] = "different"
        with self.assertRaisesRegex(studio.StudioError, "provenance"):
            studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)

    @unittest.skipUnless(FFMPEG and FFPROBE and FONT, "FFmpeg, ffprobe and a test font are required")
    def test_timed_narration_renders_over_moving_video(self):
        source = self.root / "moving.mp4"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc2=s=160x240:r=10:d=1", "-vf", "drawbox=x=0:y=140:w=160:h=100:color=black:t=fill",
                        "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", str(source)], check=True)
        audio = self.root / "source.mp3"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=1", str(audio)], check=True)
        self.project["scenes"] = [{"duration": 0.6, "text": "one two",
                                   "visual": {"type": "file", "media": "video", "path": str(source)}}]
        self.project["narration"] = {"provider": "edge", "voice": "test-voice"}
        self.project["caption_font"] = "Arial"
        self.project["font_size"] = 20
        root, config = self.load()

        async def fake_synthesize(text, voice, path):
            shutil.copyfile(audio, path)
            return [{"text": "one", "start": 0.1, "end": 0.4},
                    {"text": "two", "start": 0.5, "end": 0.9}]

        with patch.object(speech, "synthesize", side_effect=fake_synthesize):
            speech.narrate(root, config)
        with self.assertRaisesRegex(studio.StudioError, "approval"):
            studio.render(root, config)
        studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)
        output = root / "output" / "test.mp4"
        probe = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)],
                               capture_output=True, text=True, check=True)
        result = json.loads(probe.stdout)
        self.assertEqual([stream["codec_type"] for stream in result["streams"]], ["video", "audio"])
        self.assertGreater(float(result["format"]["duration"]), 1.0)
        frame = subprocess.run([FFMPEG, "-v", "error", "-ss", "0.2", "-i", str(output), "-frames:v", "1",
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        caption_region = frame[150 * 160 * 3:210 * 160 * 3]
        self.assertTrue(any(caption_region[i] > 180 and caption_region[i + 1] > 180 and caption_region[i + 2] < 110
                            for i in range(0, len(caption_region) - 2, 3)), "Expected yellow caption pixels")
        self.assertTrue(any(caption_region[i] > 180 and caption_region[i + 1] > 180 and caption_region[i + 2] > 180
                            for i in range(0, len(caption_region) - 2, 3)), "Expected white caption pixels")
        config["scenes"][0]["text"] = "changed"
        with self.assertRaisesRegex(studio.StudioError, "Narration does not match"):
            studio.render(root, config, approval=studio.FINAL_EXPORT_APPROVAL)


if __name__ == "__main__":
    unittest.main()

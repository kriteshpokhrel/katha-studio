import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from katha import reel, scenes, sound
from katha.studio import StudioError

try:
    import numpy as np
except ImportError:
    np = None


class SceneTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = {
            "title": "Scene proof", "topic": "Test", "profile": "visual_storytelling",
            "scenes": {"model": {"description": "A moving disc", "objects": [
                {"id": "disc", "type": "circle", "attrs": {"r": 50, "fill": "accent"}},
                {"id": "label", "type": "text", "text": "<script>", "attrs": {"fill": "ink"}},
            ]}},
            "beats": [
                {"say": "एक दुई", "keyword": "एक", "visual": {
                    "type": "scene", "scene": "model", "purpose": "Move the same disc",
                    "actions": [{"target": "disc", "cue": "दुई", "duration": 1,
                                 "to": {"x": 100}, "meaning": "Trace its route"}]}},
                {"say": "तीन चार", "keyword": "तीन", "visual": {
                    "type": "scene", "scene": "model", "purpose": "Continue its route",
                    "actions": [{"target": "disc", "duration": 2,
                                 "to": {"x": 200}, "meaning": "Continue moving"}]}},
                {"say": "कमेन्ट गर्नुहोस्", "keyword": "कमेन्ट", "visual": {"type": "outro"}},
            ],
        }
        self.times = [(0, 3), (3, 6), (6, 9)]
        self.words = [[{"text": text, "start": start + n, "end": start + n + 0.3}
                       for n, text in enumerate(beat["say"].split())]
                      for beat, (start, _) in zip(self.config["beats"], self.times)]

    def load(self):
        path = self.root / "project.json"
        path.write_text(json.dumps(self.config), encoding="utf-8")
        return reel.load_reel(path)

    def render(self):
        _, config = self.load()
        return scenes.render(config, self.words, self.times, {}, reel.cue_time)

    def test_persistent_scene_and_cued_actions(self):
        markup, payload, events = self.render()
        self.assertEqual(markup.count('id="scene-model-disc"'), 1)
        self.assertIn('data-scene-duration="6"', markup)
        self.assertIn("&lt;script&gt;", markup)
        plan = json.loads(payload)
        self.assertEqual([a["at"] for a in plan], [1, 3])
        self.assertEqual([a["to"] for a in plan], [{"x": 100}, {"x": 200}])
        self.assertIn(2, events[0])

    def test_bad_scene_object_and_action_inputs_fail_cleanly(self):
        cases = [
            (lambda c: c["scenes"]["model"]["objects"].append(
                {"id": "disc", "type": "circle", "attrs": {"r": 10}}), "duplicate"),
            (lambda c: c["scenes"]["model"]["objects"][0]["attrs"].update(onload="alert(1)"), "unsupported attribute"),
            (lambda c: c["scenes"]["model"]["objects"][0]["attrs"].clear(), "geometry"),
            (lambda c: c["scenes"]["model"]["objects"][0].update(opacity=float("nan")), "finite"),
            (lambda c: c["beats"][0]["visual"].update(scene=[]), "unknown scene"),
            (lambda c: c["beats"][0]["visual"]["actions"][0].update(target=[]), "unknown target"),
            (lambda c: c["beats"][0]["visual"]["actions"][0].update(easing="typo"), "unsupported fields"),
            (lambda c: c["beats"][0]["visual"]["actions"][0].update(to={"phase": 90}), "phase object"),
        ]
        original = copy.deepcopy(self.config)
        for mutate, error in cases:
            with self.subTest(error=error):
                self.config = copy.deepcopy(original)
                mutate(self.config)
                with self.assertRaisesRegex(StudioError, error):
                    self.load()

    def test_scene_cannot_reappear_after_another_component(self):
        self.config["beats"].insert(1, {"say": "बीचमा", "keyword": "बीचमा",
                                              "visual": {"type": "card", "title": "Break"}})
        with self.assertRaisesRegex(StudioError, "consecutive"):
            self.load()

    def test_overlapping_and_out_of_beat_actions_fail(self):
        action = self.config["beats"][0]["visual"]["actions"][0]
        action["duration"] = 2.5
        with self.assertRaisesRegex(StudioError, "exceeds"):
            self.render()
        action["duration"] = 1
        self.config["beats"][0]["visual"]["actions"].append(
            {"target": "disc", "cue": "दुई", "duration": 1, "to": {"x": 200}, "meaning": "Conflict"})
        with self.assertRaisesRegex(StudioError, "overlapping"):
            self.render()

    def test_caption_and_text_motion_do_not_count_as_picture(self):
        self.config["scenes"]["model"]["objects"] = [
            {"id": "label", "type": "text", "text": "Text only"}]
        for beat in self.config["beats"][:2]:
            beat["visual"]["actions"] = [
                {"target": "label", "duration": 2, "to": {"x": 200}, "meaning": "Moving text"}]
        _, config = self.load()
        _, _, events = scenes.render(config, self.words, self.times, {}, reel.cue_time)
        self.assertEqual(events[0], [0])
        checks = reel.storytelling_checks(config, self.times)
        self.assertEqual([c["value"] for c in checks], [0, 2])
        self.assertTrue(all(not c["pass"] for c in checks))
        config["profile"] = "legacy"
        self.assertEqual(reel.storytelling_checks(config, self.times), [])

    def test_only_explicit_effects_are_emitted(self):
        _, config = self.load()
        _, effects, _ = reel.composition(config, self.words, self.times, {})
        self.assertEqual(effects, [])
        self.config["beats"][0]["sound"] = {"kind": "pop", "cue": "दुई"}
        _, config = self.load()
        _, effects, _ = reel.composition(config, self.words, self.times, {})
        self.assertEqual(effects, [(1, "pop")])

    def test_invalid_audio_controls_fail_before_render(self):
        for field, value in (("volume", -1), ("duck_ratio", 0), ("seed", -3),
                             ("bpm", "fast"), ("asset", [])):
            with self.subTest(field=field):
                self.config["music"] = {field: value}
                with self.assertRaisesRegex(StudioError, "music"):
                    self.load()

    def test_mix_keeps_music_and_effect_gains_independent(self):
        with patch("katha.reel.execute") as run, patch("katha.reel.tool", return_value="ffmpeg"):
            reel.mix("silent", "voice", "music", "effects", 0.4, 9, "out",
                     sfx_volume=0.15, duck_ratio=2)
        args = run.call_args.args[0]
        graph = args[args.index("-filter_complex") + 1]
        self.assertIn("[2:a]volume=0.4", graph)
        self.assertIn("[3:a]volume=0.15,lowpass=f=3000", graph)
        self.assertIn("ratio=2:", graph)

    def asset(self, kind, src):
        self.config["assets"] = {"sample": {
            "src": src, "kind": kind, "origin": "original", "credit": "Test artwork",
            "license": "Original test fixture",
        }}

    def test_asset_rights_and_missing_files_are_errors(self):
        self.asset("image", "missing.png")
        self.config["assets"]["sample"]["origin"] = "licensed"
        with self.assertRaisesRegex(StudioError, "source"):
            self.load()
        self.config["assets"]["sample"]["source"] = "https://example.com/license"
        self.config["assets"]["sample"]["credit"] = ""
        with self.assertRaisesRegex(StudioError, "credit"):
            self.load()
        self.config["assets"]["sample"]["credit"] = "Artist"
        _, config = self.load()
        with self.assertRaisesRegex(StudioError, "not found"):
            scenes.collect(config, self.root, self.root, self.times)

    def test_asset_content_change_invalidates_export_fingerprint(self):
        self.asset("image", "drawing.png")
        media = self.root / "drawing.png"
        media.write_bytes(b"first")
        path, config = self.load()
        first = reel.project_fingerprint(path, config)
        media.write_bytes(b"second")
        self.assertNotEqual(first, reel.project_fingerprint(path, config))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_actual_local_image_video_audio_and_short_video_rejection(self):
        for kind, filename, arguments in [
            ("image", "test.png", ["-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1"]),
            ("video", "test.mp4", ["-f", "lavfi", "-i", "testsrc2=s=64x64:r=30:d=6", "-an", "-c:v", "libx264"]),
            ("audio", "test.wav", ["-f", "lavfi", "-i", "sine=frequency=220:duration=1"]),
        ]:
            with self.subTest(kind=kind):
                subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-y", *arguments, str(self.root / filename)],
                               check=True, capture_output=True)
                self.asset(kind, filename)
                if kind != "audio":
                    self.config["scenes"]["model"]["objects"] = [
                        {"id": "disc", "type": kind, "asset": "sample", "attrs": {"width": 300, "height": 200}}]
                else:
                    self.config["music"] = {"asset": "sample"}
                    self.config["scenes"]["model"]["objects"] = [
                        {"id": "disc", "type": "circle", "attrs": {"r": 50}}]
                _, config = self.load()
                destination = self.root / ("collected-" + kind)
                destination.mkdir()
                paths = scenes.collect(config, self.root, destination, self.times)
                markup, _, _ = scenes.render(config, self.words, self.times, paths, reel.cue_time)
                if kind == "video":
                    self.assertIn('data-duration="6" data-volume="0"', markup)
                    with self.assertRaisesRegex(StudioError, "needs 7"):
                        scenes.collect(config, self.root, destination, [(0, 3), (3, 7), (7, 9)])
                elif kind == "image":
                    self.assertIn('href="assets/media-sample.png"', markup)
                else:
                    self.assertEqual(paths, {})
                (self.root / filename).write_bytes(b"corrupt")
                with self.assertRaisesRegex(StudioError, "not usable"):
                    scenes.collect(config, self.root, destination, self.times)

    @unittest.skipIf(np is None, "numpy required")
    def test_music_is_finite_seeded_and_effects_are_sparse(self):
        first = sound.music_bed(2, bpm=78, seed=12)
        self.assertTrue(np.isfinite(first).all())
        np.testing.assert_array_equal(first, sound.music_bed(2, bpm=78, seed=12))
        self.assertFalse(np.array_equal(first, sound.music_bed(2, bpm=78, seed=13)))
        effects = sound.sfx_track(2, [(0.5, "pop")])
        self.assertFalse(effects[:int(0.5 * sound.RATE)].any())
        self.assertLess(float(np.abs(effects).max()), 0.2)
        self.assertEqual(sound.sfx_track(2, []).max(), 0)

    @unittest.skipUnless(os.environ.get("KATHA_RENDER_MEDIA_TEST") == "1", "opt-in HyperFrames media render")
    def test_local_media_render_is_visible_and_video_changes(self):
        destination = self.root / "composition"
        assets = destination / "assets"
        assets.mkdir(parents=True)
        for filename, arguments in [
            ("image.png", ["-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1"]),
            ("video.mp4", ["-f", "lavfi", "-i", "testsrc2=s=320x240:r=30:d=6", "-an", "-c:v", "libx264"]),
        ]:
            subprocess.run([shutil.which("ffmpeg"), "-v", "error", "-y", *arguments, str(self.root / filename)],
                           check=True, capture_output=True)
        self.config["assets"] = {
            kind: {"kind": kind, "src": filename, "origin": "original", "credit": "FFmpeg test",
                   "license": "Original synthetic fixture"}
            for kind, filename in [("image", "image.png"), ("video", "video.mp4")]
        }
        self.config["scenes"]["model"]["objects"] = [
            {"id": "still", "type": "image", "asset": "image", "attrs": {"width": 150, "height": 100}},
            {"id": "moving", "type": "video", "asset": "video", "x": 200, "y": 100,
             "attrs": {"width": 400, "height": 300}},
        ]
        for beat in self.config["beats"][:2]:
            beat["visual"]["actions"] = []
        _, config = self.load()
        paths = scenes.collect(config, self.root, assets, self.times)
        page, _, _ = reel.composition(config, self.words, self.times, paths)
        (destination / "index.html").write_text(page, encoding="utf-8")
        shutil.copytree(config["_brand"]["_fonts"], assets / "fonts")
        shutil.copyfile(reel.ASSETS / "reel.js", assets / "reel.js")
        shutil.copyfile(reel.REPO / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")
        output = self.root / "proof.mp4"
        reel.render_video(destination, output)
        first, later = reel.frame_at(output, 1), reel.frame_at(output, 4)
        self.assertGreater(float(first[690:750, 140:240, 0].mean()), 220)
        self.assertLess(float(first[690:750, 140:240, 1].mean()), 30)
        self.assertGreater(float(np.abs(first[790:1050, 340:690] - later[790:1050, 340:690]).mean()), 2)


if __name__ == "__main__":
    unittest.main()

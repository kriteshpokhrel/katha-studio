import json
from pathlib import Path
import tempfile
import unittest

from katha import reel
from katha.studio import FINAL_EXPORT_APPROVAL, StudioError

try:
    import numpy as np
except ImportError:
    np = None


def words(*items):
    return [{"text": text, "start": start, "end": start + 0.3} for text, start in items]


class ReelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = {
            "title": "Test", "topic": "Topic",
            "beats": [
                {"say": "पहिलो कुरा यहाँ", "keyword": "कुरा", "visual": {"type": "card", "title": "One"}},
                {"say": "दोस्रो कुरा", "keyword": "दोस्रो", "step": 1, "visual": {"type": "stamp", "text": "OK"}},
                {"say": "कमेन्ट गर्नुहोस्", "keyword": "कमेन्ट", "visual": {"type": "outro"}},
            ],
        }

    def write(self, config=None):
        path = self.root / "project.json"
        path.write_text(json.dumps(config or self.config, ensure_ascii=False), encoding="utf-8")
        return path

    def assert_invalid(self, message):
        with self.assertRaisesRegex(StudioError, message):
            reel.load_reel(self.write())

    def test_valid_project_gets_defaults_and_brand(self):
        _, config = reel.load_reel(self.write())
        self.assertEqual(config["voice"]["name"], "ne-NP-SagarNeural")
        self.assertEqual(config["_brand"]["mark"], "क")

    def test_outro_must_be_last_beat(self):
        self.config["beats"][0]["visual"] = {"type": "outro"}
        self.assert_invalid("last beat")

    def test_step_numbers_must_not_skip(self):
        self.config["beats"][1]["step"] = 2
        self.assert_invalid("without gaps")

    def test_downloaded_photo_requires_credit(self):
        self.config["beats"][0]["visual"] = {"type": "photo", "url": "https://example.com/a.jpg"}
        self.assert_invalid("credit")

    def test_rejects_invalid_voice_rate(self):
        self.config["voice"] = {"rate": "fast"}
        self.assert_invalid("voice.rate")

    def test_align_splits_words_per_beat_and_keeps_display_text(self):
        beats = [{"say": "नमस्ते, साथी!"}, {"say": "फेरि भेटौँ"}]
        spoken = words(("नमस्ते", 0.0), ("साथी", 0.4), ("फेरि", 1.0), ("भेटौँ", 1.4))
        result = reel.align(beats, spoken)
        self.assertEqual([[w["text"] for w in beat] for beat in result], [["नमस्ते,", "साथी!"], ["फेरि", "भेटौँ"]])

    def test_align_reports_mismatch(self):
        with self.assertRaisesRegex(StudioError, "beat 1"):
            reel.align([{"say": "एक दुई"}], words(("एक", 0.0), ("तीन", 0.4)))
        with self.assertRaisesRegex(StudioError, "extra words"):
            reel.align([{"say": "एक"}], words(("एक", 0.0), ("दुई", 0.4)))

    def test_timing_starts_at_zero_and_adds_tail(self):
        beat_words = [words(("a", 0.2)), words(("b", 1.5), ("c", 2.0))]
        self.assertEqual(reel.timing(beat_words, 2.0), [(0.0, 1.38), (1.38, 4.3)])

    def test_keyword_span_matches_whole_words_only(self):
        line = words(("जेन्सन", 0), ("हुआङ,", 1), ("सीईओ", 2))
        self.assertEqual(reel.keyword_span(line, "जेन्सन हुआङ", 1), (0, 1))
        with self.assertRaisesRegex(StudioError, "keyword"):
            reel.keyword_span(line, "जेन्स", 1)

    def test_caption_groups_multi_word_keyword(self):
        brand = reel.load_brand(reel.REPO / "brand" / "brand.json")
        line = words(("जेन्सन", 0.5), ("हुआङ", 0.8), ("फर्किए", 1.1))
        html = reel.caption(2, {"keyword": "जेन्सन हुआङ"}, line, 0.4, 2.0, brand, False)
        self.assertEqual(html.count('class="kwg"'), 1)
        self.assertEqual(html.count('class="w kw"'), 2)
        self.assertIn("out@1.800", html)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_motion_metrics_measures_longest_hold(self):
        frames = np.zeros((8, 4, 4), dtype=np.float32)
        frames[1:3] = 50
        frames[6:] = 100
        metrics = reel.motion_metrics(frames, 0.25)
        self.assertEqual(metrics["max_hold"], 0.5)
        self.assertAlmostEqual(metrics["moving_share"], round(3 / 7, 3))

    @unittest.skipIf(np is None, "numpy not installed")
    def test_outside_ink_ignores_text_box(self):
        frame = np.full((reel.HEIGHT, reel.WIDTH, 3), 240, dtype=np.int16)
        frame[500:510, 500:510] = 0
        self.assertEqual(reel.outside_ink(frame, (240, 240, 240)), 0)
        frame[10:12, 10:15] = 0
        self.assertEqual(reel.outside_ink(frame, (240, 240, 240)), 10)

    def test_export_requires_exact_approval_and_reviewed_preview(self):
        path = self.write()
        with self.assertRaisesRegex(StudioError, "exact approval"):
            reel.reel(path, approval="final export")
        with self.assertRaisesRegex(StudioError, "No reviewed preview"):
            reel.reel(path, approval=FINAL_EXPORT_APPROVAL)

    def test_export_rejects_stale_or_failed_preview(self):
        path = self.write()
        output = self.root / "output"
        output.mkdir()
        (output / "project.mp4").write_bytes(b"video")
        qa = output / "project-qa.json"
        qa.write_text(json.dumps({"passed": True, "fingerprint": "old"}), encoding="utf-8")
        with self.assertRaisesRegex(StudioError, "changed since"):
            reel.reel(path, approval=FINAL_EXPORT_APPROVAL)
        _, config = reel.load_reel(path)
        qa.write_text(json.dumps({"passed": False, "fingerprint": reel.project_fingerprint(path, config)}), encoding="utf-8")
        with self.assertRaisesRegex(StudioError, "failed quality"):
            reel.reel(path, approval=FINAL_EXPORT_APPROVAL)
        qa.write_text(json.dumps({"passed": True, "fingerprint": reel.project_fingerprint(path, config)}), encoding="utf-8")
        self.assertEqual(reel.reel(path, approval=FINAL_EXPORT_APPROVAL), 0)
        self.assertEqual((self.root / "Exports" / "project.mp4").read_bytes(), b"video")


if __name__ == "__main__":
    unittest.main()

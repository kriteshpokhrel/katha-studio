import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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

    def test_align_preserves_script_when_provider_splits_a_word(self):
        beats = [{"say": "नमस्ते, साथी!"}]
        spoken = words(("नम", 0.0), ("स्ते", 0.4), ("साथी", 0.8))
        aligned = reel.align(beats, spoken)[0]
        self.assertEqual([word["text"] for word in aligned], ["नमस्ते,", "साथी!"])
        self.assertEqual((aligned[0]["start"], aligned[0]["end"]), (0.0, 0.7))

    def test_align_keeps_display_text_with_multiword_pronunciation(self):
        beats = [{"say": "NVIDIA 1993 मा", "pronunciations": {
            "NVIDIA": "एनभिडिया", "1993": "उन्नाइस सय त्रियानब्बे"}}]
        spoken = words(("एनभिडिया", 0.0), ("उन्नाइस", 0.4), ("सय", 0.8),
                       ("त्रियानब्बे", 1.2), ("मा", 1.6))
        aligned = reel.align(beats, spoken)[0]
        self.assertEqual([word["text"] for word in aligned], ["NVIDIA", "1993", "मा"])
        self.assertEqual((aligned[1]["start"], aligned[1]["end"]), (0.4, 1.5))
        self.assertEqual(reel.keyword_span(aligned, "1993", 1), (1, 1))

    def test_align_rejects_provider_token_crossing_display_words(self):
        with self.assertRaisesRegex(StudioError, "beat 1 word"):
            reel.align([{"say": "एक दुई"}], words(("एकदुई", 0.0)))

    def test_align_rejects_invalid_or_unordered_timestamps(self):
        beats = [{"say": "एक दुई"}]
        with self.assertRaisesRegex(StudioError, "invalid"):
            reel.align(beats, [{"text": "एक", "start": float("nan"), "end": 1.0}])
        with self.assertRaisesRegex(StudioError, "ordered"):
            reel.align(beats, words(("एक", 1.0), ("दुई", 0.0)))

    def test_pronunciation_rejects_unknown_or_empty_replacement(self):
        self.config["beats"][0]["pronunciations"] = {"missing": "शब्द"}
        self.assert_invalid("does not match")
        self.config["beats"][0]["pronunciations"] = {"पहिलो": " "}
        self.assert_invalid("non-empty")

    def test_narration_uses_pronunciation_overrides(self):
        beats = [{"say": "NVIDIA फर्कियो", "pronunciations": {"NVIDIA": "एनभिडिया"}}]
        config = {"beats": beats, "voice": {"name": "test", "rate": "+0%", "pitch": "+0Hz"}}
        calls = []

        async def fake_synthesize(text, voice, path, rate, pitch):
            calls.append(text)
            path.write_bytes(b"audio")
            return words(("एनभिडिया", 0), ("फर्कियो", 1))

        with patch("katha.speech.synthesize", fake_synthesize):
            reel.narrate(config, self.root)
        self.assertEqual(calls, ["एनभिडिया फर्कियो"])

    def test_scribe_narration_reads_words_and_fingerprints_inputs(self):
        audio = self.root / "voice.mp3"
        audio.write_bytes(b"voice")
        timeline = self.root / "scribe.json"
        timeline.write_text(json.dumps({"segments": [{"words": [
            {"text": "पहिलो", "start_time": 0.1, "end_time": 0.4},
            {"text": " ", "start_time": 0.4, "end_time": 0.5},
            {"text": "कुरा", "start_time": 0.5, "end_time": 0.8},
        ]}]}), encoding="utf-8")
        self.config["voice"] = {"provider": "scribe", "audio": "voice.mp3", "timestamps": "scribe.json"}
        path, config = reel.load_reel(self.write())
        imported_audio, imported_words = reel.narrate(config, self.root, self.root)
        self.assertEqual(imported_audio, audio)
        self.assertEqual(imported_words, [{"text": "पहिलो", "start": 0.1, "end": 0.4},
                                          {"text": "कुरा", "start": 0.5, "end": 0.8}])
        before = reel.project_fingerprint(path, config)
        audio.write_bytes(b"different")
        self.assertNotEqual(before, reel.project_fingerprint(path, config))
        before = reel.project_fingerprint(path, config)
        timeline.write_text("{}", encoding="utf-8")
        self.assertNotEqual(before, reel.project_fingerprint(path, config))
        with self.assertRaisesRegex(StudioError, "must contain segments"):
            reel.narrate(config, self.root, self.root)

    def test_scribe_narration_rejects_missing_or_malformed_inputs(self):
        self.config["voice"] = {"provider": "scribe", "audio": "voice.mp3", "timestamps": "scribe.json"}
        _, config = reel.load_reel(self.write())
        with self.assertRaisesRegex(StudioError, "audio not found"):
            reel.narrate(config, self.root, self.root)
        (self.root / "voice.mp3").write_bytes(b"voice")
        (self.root / "scribe.json").write_text('{"segments":[{"words":[{"text":"x"}]}]}', encoding="utf-8")
        _, imported = reel.narrate(config, self.root, self.root)
        with self.assertRaisesRegex(StudioError, "invalid"):
            reel.align([{"say": "x"}], imported)
        (self.root / "scribe.json").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(StudioError, "Cannot read Scribe timestamps"):
            reel.narrate(config, self.root, self.root)

    def story_config(self):
        self.config["beats"] = [
            {"say": "किन यस्तो हुन्छ?", "keyword": "किन", "visual": {"type": "stamp", "text": "?"}},
            {"say": "यो कुरा,", "keyword": "कुरा", "visual": {"type": "stamp", "text": "A"}},
            {"say": "यहाँ बुझिन्छ।", "keyword": "बुझिन्छ", "visual": {"type": "stamp", "text": "B"}},
            {"say": "कमेन्ट गर्नुहोस्", "keyword": "कमेन्ट", "visual": {"type": "outro"}},
        ]
        self.config["story"] = {
            "audience": "Nepali learners", "takeaway": "Understand one connection", "target_seconds": 25,
            "hooks": ["किन यस्तो हुन्छ?", "यो कसरी सम्भव छ?", "यसको कारण के होला?"],
            "selected_hook": 0,
            "sections": [
                {"role": "hook", "text": "किन यस्तो हुन्छ?"},
                {"role": "explanation", "text": "यो कुरा, यहाँ बुझिन्छ।"},
                {"role": "cta", "text": "कमेन्ट गर्नुहोस्"},
            ],
        }

    def test_story_maps_one_sentence_to_multiple_caption_beats(self):
        self.story_config()
        _, config = reel.load_reel(self.write())
        sections = reel.story_sections(config)
        self.assertEqual((sections[1]["first"], sections[1]["last"]), (1, 2))
        captured = []

        async def fake_synthesize(text, voice, path, rate, pitch):
            captured.append(text)
            path.write_bytes(b"audio")
            return words(("किन", 0), ("यस्तो", .4), ("हुन्छ", .8), ("यो", 1.2), ("कुरा", 1.6),
                         ("यहाँ", 2), ("बुझिन्छ", 2.4), ("कमेन्ट", 2.8), ("गर्नुहोस्", 3.2))

        with patch("katha.speech.synthesize", fake_synthesize):
            _, provider_words = reel.narrate(config, self.root)
        self.assertEqual(captured, ["किन यस्तो हुन्छ? यो कुरा, यहाँ बुझिन्छ। कमेन्ट गर्नुहोस्"])
        self.assertEqual(reel.align(config["beats"], provider_words)[2][0]["text"], "यहाँ")

    def test_story_rejects_text_drift_punctuation_and_split_section_boundaries(self):
        for text in ("यो कुरा। यहाँ बुझिन्छ।", "यो कुरा, यहाँ हराउँछ।", "यो कुरा, यहाँ"):
            with self.subTest(text=text):
                self.story_config()
                self.config["story"]["sections"][1]["text"] = text
                self.assert_invalid("match consecutive beat captions exactly")
        self.story_config()
        self.config["story"]["sections"][1]["text"] = "यो कुरा,"
        self.config["story"]["sections"][-1]["text"] = "यहाँ बुझिन्छ। कमेन्ट गर्नुहोस्"
        self.assert_invalid("cta must map")

    def test_story_rejects_invalid_brief_hooks_and_incomplete_coverage(self):
        cases = [
            ("audience", "", "non-empty"),
            ("target_seconds", True, "story.target_seconds"),
            ("target_seconds", float("nan"), "story.target_seconds"),
            ("selected_hook", True, "index"),
            ("selected_hook", 1, "selected hook exactly"),
            ("hooks", ["किन", "किन", "कसरी"], "distinct"),
            ("hooks", [" ".join(["word"] * 9), "किन", "कसरी"], "at most 8"),
        ]
        for field, value, message in cases:
            with self.subTest(field=field, value=value):
                self.story_config()
                self.config["story"][field] = value
                self.assert_invalid(message)
        self.story_config()
        self.config["story"]["sections"][1]["role"] = "hook"
        self.assert_invalid("only hook")
        self.story_config()
        self.config["story"]["sections"][-1]["role"] = "result"
        self.assert_invalid("only cta")
        self.story_config()
        self.config["story"]["sections"][1]["role"] = []
        self.assert_invalid("supported role")
        self.story_config()
        self.config["beats"].append(self.config["beats"][-1].copy())
        self.config["beats"][-2]["visual"] = {"type": "stamp", "text": "Extra"}
        self.assert_invalid("cta must map")

    def test_story_rejects_overlong_caption_without_limiting_sentence_length(self):
        self.story_config()
        text = "one two three four five six seven eight nine ten eleven"
        self.config["beats"][1]["say"] = text
        self.config["beats"][1]["keyword"] = "one"
        self.config["story"]["sections"][1]["text"] = text + " यहाँ बुझिन्छ।"
        self.assert_invalid("caption exceeds 10 words")

    def test_story_timing_failure_writes_plan_without_rendering(self):
        self.story_config()
        path = self.write()
        beat_words = [words(("किन", .1)), words(("यो", 2.1)),
                      words(("यहाँ", 4.1)), words(("कमेन्ट", 6.1))]
        times = [(0, 2), (2, 4), (4, 6), (6, 9)]
        events = [[0], [2], [4], [6]]
        result = (self.root / "voice.mp3", sum(beat_words, []), beat_words, times, [], events)
        with patch("katha.reel.build", return_value=result), patch("katha.reel.audio_duration", return_value=7), \
                patch("katha.reel.render_video") as render:
            with self.assertRaisesRegex(StudioError, "story_target_seconds"):
                reel.reel(path)
        render.assert_not_called()
        plan = (self.root / "output" / "project-storyboard.md").read_text(encoding="utf-8")
        self.assertIn("यो कुरा, यहाँ बुझिन्छ।", plan)
        self.assertIn("Nepali learners", plan)
        self.assertIn("[selected]", plan)
        self.assertTrue(reel.story_timing_checks(self.config, [(0, 25)])[0]["pass"])

    def test_visual_pacing_counts_story_reveals_not_beat_motion(self):
        times = [(0.0, 5.5), (5.5, 8.0), (8.0, 12.0)]
        checks = reel.visual_pacing(times, [[0.0, 2.8], [5.5], [8.0]])
        self.assertTrue(all(check["pass"] for check in checks))
        checks = reel.visual_pacing(times, [[0.0], [5.5], [8.0]])
        self.assertFalse(checks[0]["pass"])
        self.assertEqual(checks[0]["value"], 5.5)

    def test_card_cue_schedules_a_story_reveal(self):
        brand = reel.load_brand(reel.REPO / "brand" / "brand.json")
        beat = {"visual": {"type": "card", "title": "Context",
                           "lines": [{"text": "Next fact", "cue": "दुई"}]}}
        builder = reel.Beat(1, beat, words(("एक", 0.1), ("दुई", 2.5)), 0.0, 5.0, brand, {})
        markup = builder.html()
        self.assertIn("rise@2.500", markup)
        self.assertEqual(builder.visual_events, [0.0, 2.5])
        self.assertTrue(reel.visual_pacing([(0.0, 5.0), (5.0, 8.0)],
                                           [builder.visual_events, [5.0]])[0]["pass"])

    def test_visual_pacing_rejects_reveals_outside_beat(self):
        with self.assertRaisesRegex(StudioError, "outside"):
            reel.visual_pacing([(0.0, 3.0), (3.0, 6.0)], [[0.0, 3.0], [3.0]])

    def test_pacing_failure_writes_plan_before_render(self):
        path = self.write()
        beat_words = [words(("पहिलो", 0.1)), words(("दोस्रो", 5.2)), words(("कमेन्ट", 7.7))]
        times = [(0.0, 5.0), (5.0, 7.5), (7.5, 10.0)]
        events = [[0.0], [5.0], [7.5]]
        result = (self.root / "voice.mp3", sum(beat_words, []), beat_words, times, [], events)
        with patch("katha.reel.build", return_value=result), patch("katha.reel.audio_duration", return_value=8), \
                patch("katha.reel.render_video") as render:
            with self.assertRaisesRegex(StudioError, "reveal gap"):
                reel.reel(path)
        render.assert_not_called()
        plan = (self.root / "output" / "project-storyboard.md").read_text(encoding="utf-8")
        self.assertIn("पहिलो कुरा यहाँ", plan)
        self.assertIn("Reveals", plan)

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

    def test_outro_has_separate_layout_without_float_or_pulsing_cta(self):
        _, config = reel.load_reel(self.write())
        beat_words = [words(("पहिलो", 0), ("कुरा", 0.4), ("यहाँ", 0.8)),
                      words(("दोस्रो", 3), ("कुरा", 3.4)),
                      words(("कमेन्ट", 6), ("गर्नुहोस्", 6.4))]
        page, _, _ = reel.composition(config, beat_words, [(0, 3), (3, 6), (6, 10)], {})
        self.assertIn('class="stage outro-stage"', page)
        outro = reel.Beat(3, config["beats"][-1], beat_words[-1], 6, 10,
                          config["_brand"], {}).html()
        self.assertIn('class="outro-action"', outro)
        self.assertNotIn("pulse@", outro)
        self.assertNotIn("float@6.", page)
        self.assertIn('class="handle mono"', outro)

    @unittest.skipIf(np is None, "numpy not installed")
    def test_motion_metrics_measures_longest_hold(self):
        frames = np.zeros((8, 4, 4), dtype=np.float32)
        frames[1:3] = 50
        frames[6:] = 100
        metrics = reel.motion_metrics(frames, 0.25)
        self.assertEqual(metrics["max_hold"], 0.5)
        self.assertAlmostEqual(metrics["moving_share"], round(3 / 7, 3))

    @unittest.skipIf(np is None, "numpy not installed")
    def test_story_motion_excludes_closing_hold_but_not_static_content(self):
        _, config = reel.load_reel(self.write())
        config["profile"] = "visual_storytelling"
        beat_words = [words(("पहिलो", 0), ("कुरा", 0.4)),
                      words(("दोस्रो", 3), ("कुरा", 3.4)),
                      words(("कमेन्ट", 6), ("गर्नुहोस्", 6.4))]
        frames = np.zeros((40, 320, 180), dtype=np.float32)
        frames[:24] = np.arange(24)[:, None, None] * 5
        frames[24:] = frames[23]
        with patch("katha.reel.gray_frames", return_value=frames), \
                patch("katha.reel.loudness", return_value=(-14, -2)), \
                patch("katha.reel.frame_at"), patch("katha.reel.outside_ink", return_value=0):
            report = reel.quality("preview", config, sum(beat_words, []), beat_words,
                                  [(0, 3), (3, 6), (6, 10)], [[0], [3], [6]])
            hold = next(c for c in report["checks"] if c["check"] == "longest_static_hold_seconds")
            self.assertTrue(hold["pass"])
            frames[4:24] = frames[3]
            report = reel.quality("preview", config, sum(beat_words, []), beat_words,
                                  [(0, 3), (3, 6), (6, 10)], [[0], [3], [6]])
            hold = next(c for c in report["checks"] if c["check"] == "longest_static_hold_seconds")
            self.assertFalse(hold["pass"])

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
        qa.write_text(json.dumps({"passed": True, "fingerprint": reel.project_fingerprint(path, config),
                                  "preview_sha256": reel.preview_hash(output / "project.mp4")}), encoding="utf-8")
        self.assertEqual(reel.reel(path, approval=FINAL_EXPORT_APPROVAL), 0)
        self.assertEqual((self.root / "Exports" / "project.mp4").read_bytes(), b"video")
        (output / "project.mp4").write_bytes(b"changed")
        with self.assertRaisesRegex(StudioError, "Preview changed"):
            reel.reel(path, approval=FINAL_EXPORT_APPROVAL)

    def test_failed_rebuild_invalidates_previous_quality_report(self):
        path = self.write()
        output = self.root / "output"
        output.mkdir()
        qa = output / "project-qa.json"
        qa.write_text("{}", encoding="utf-8")
        with patch("katha.reel.build", side_effect=StudioError("build failed")):
            with self.assertRaisesRegex(StudioError, "build failed"):
                reel.reel(path)
        self.assertFalse(qa.exists())


if __name__ == "__main__":
    unittest.main()

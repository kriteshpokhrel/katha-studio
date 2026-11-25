"""Beat-based branded reel pipeline: script -> narration -> HyperFrames composition -> mix -> QA -> export.

Every beat is one short spoken line with a highlighted keyword and one visual component. Narration word
timestamps drive every caption word, component reveal and sound effect, so the frame follows the voice.
"""
import asyncio
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .studio import FINAL_EXPORT_APPROVAL, StudioError, audio_duration, request_bytes

REPO = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / "reel_assets"
WIDTH, HEIGHT, FPS = 1080, 1920, 30
VISUALS = ("photo", "card", "swap", "counter", "stamp", "checklist", "list", "timeline", "outro")
TEXT_BOX = (65, 270, 916, 1250)
COLOR_KEYS = ("paper", "dot", "ink", "muted", "line", "card", "accent", "on_accent")
LIMITS = {
    "duration": (20.0, 150.0), "words_per_second": (1.8, 3.4), "beat_seconds": (1.0, 6.0),
    "outro_seconds": (2.0, 9.0), "beat_words": 10, "lufs": (-15.5, -12.5), "true_peak": -1.0,
    "moving_share": 0.35, "max_hold": 1.25, "visual_gap": 3.0,
}


def _text(value, label, required=True):
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise StudioError(f"{label} must be non-empty text")
    return value.strip()


def _items(visual, label, minimum=1, maximum=5):
    items = visual.get("items")
    if not isinstance(items, list) or not minimum <= len(items) <= maximum:
        raise StudioError(f"{label}.items must be a list of {minimum}-{maximum} entries")
    return [item if isinstance(item, dict) else {"text": item} for item in items]


def load_reel(path):
    path = Path(path).resolve()
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StudioError(f"Cannot read reel project {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise StudioError("Reel project must be a JSON object")
    _text(config.get("title"), "title")
    _text(config.get("topic"), "topic")
    voice = config.setdefault("voice", {})
    if not isinstance(voice, dict) or voice.get("provider", "edge") != "edge":
        raise StudioError("voice.provider must be edge")
    voice.setdefault("name", "ne-NP-SagarNeural")
    voice.setdefault("rate", "+8%")
    voice.setdefault("pitch", "+0Hz")
    if not re.fullmatch(r"[+-]\d{1,2}%", str(voice["rate"])) or not re.fullmatch(r"[+-]\d{1,3}Hz", str(voice["pitch"])):
        raise StudioError('voice.rate must look like "+8%" and voice.pitch like "-2Hz"')
    music = config.setdefault("music", {})
    if not isinstance(music, dict):
        raise StudioError("music must be an object")
    music.setdefault("seed", 7)
    music.setdefault("bpm", 94)
    music.setdefault("volume", 0.2)
    if not isinstance(music["volume"], (int, float)) or not 0 <= music["volume"] <= 1:
        raise StudioError("music.volume must be between 0 and 1")
    outro = config.setdefault("outro", {})
    outro.setdefault("tail", 2.4)
    if not isinstance(outro["tail"], (int, float)) or not 1 <= outro["tail"] <= 5:
        raise StudioError("outro.tail must be between 1 and 5 seconds")
    beats = config.get("beats")
    if not isinstance(beats, list) or not 3 <= len(beats) <= 75:
        raise StudioError("beats must be a list of 3-75 beats")
    steps = []
    for i, beat in enumerate(beats, 1):
        label = f"Beat {i}"
        if not isinstance(beat, dict):
            raise StudioError(f"{label} must be an object")
        _text(beat.get("say"), f"{label} say")
        _text(beat.get("keyword"), f"{label} keyword")
        parts = speech_parts(beat, i)
        keyword_span([{"text": text} for text, _ in parts], beat["keyword"], i)
        if "step" in beat:
            if isinstance(beat["step"], bool) or not isinstance(beat["step"], int) or beat["step"] < 1:
                raise StudioError(f"{label} step must be a positive integer")
            steps.append(beat["step"])
        visual = beat.get("visual")
        if not isinstance(visual, dict) or visual.get("type") not in VISUALS:
            raise StudioError(f"{label} visual.type must be one of {', '.join(VISUALS)}")
        kind = visual["type"]
        if (kind == "outro") != (i == len(beats)):
            raise StudioError("The last beat, and only the last beat, must use visual.type outro")
        if kind == "photo" and not (visual.get("src") or visual.get("url")):
            raise StudioError(f"{label} photo needs src (local file) or url")
        if kind == "photo" and visual.get("url") and not _text(visual.get("credit"), f"{label} photo credit", False):
            raise StudioError(f"{label} downloaded photo needs credit with author and licence")
        if kind == "card":
            _text(visual.get("title"), f"{label} card title")
        if kind == "stamp":
            _text(visual.get("text"), f"{label} stamp text")
        if kind == "swap":
            for side in ("from", "to"):
                person = visual.get(side)
                if not isinstance(person, dict):
                    raise StudioError(f"{label} swap.{side} must be an object")
                _text(person.get("name"), f"{label} swap.{side}.name")
                _text(person.get("role"), f"{label} swap.{side}.role")
        if kind == "counter" and (isinstance(visual.get("to"), bool) or not isinstance(visual.get("to"), int)):
            raise StudioError(f"{label} counter.to must be an integer")
        if kind in ("checklist", "list", "timeline"):
            for n, item in enumerate(_items(visual, f"{label} {kind}"), 1):
                _text(item.get("what" if kind == "timeline" else "text"), f"{label} {kind} item {n}")
    if steps and steps != sorted(steps):
        raise StudioError("Beat steps must not go backwards")
    if steps and sorted(set(steps)) != list(range(1, max(steps) + 1)):
        raise StudioError("Beat steps must be numbered 1..N without gaps")
    brand_path = (path.parent / config.get("brand", REPO / "brand" / "brand.json")).resolve()
    config["_brand"] = load_brand(brand_path)
    return path, config


def load_brand(path):
    try:
        brand = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise StudioError(f"Cannot read brand {path}: {exc}") from exc
    for key in ("name", "mark", "handle", "tagline"):
        _text(brand.get(key), f"brand.{key}")
    colors = brand.get("colors", {})
    for key in COLOR_KEYS:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(colors.get(key, ""))):
            raise StudioError(f"brand.colors.{key} must be a #RRGGBB color")
    fonts = (Path(path).parent / brand.get("fonts", "fonts")).resolve()
    if not fonts.is_dir() or not any(fonts.glob("*.ttf")):
        raise StudioError(f"Brand font folder not found or empty: {fonts}")
    brand["_fonts"] = fonts
    brand.setdefault("outro", {})
    return brand


def key(value):
    from .speech import spoken_text_key
    return spoken_text_key(value)


def speech_parts(beat, index):
    """Pair authoritative display tokens with optional pronunciation overrides."""
    tokens = []
    prefix = ""
    for token in beat["say"].split():
        if not key(token):
            if tokens:
                tokens[-1] += " " + token
            else:
                prefix += token + " "
        else:
            tokens.append(prefix + token)
            prefix = ""
    if not tokens:
        raise StudioError(f"Beat {index} say must contain spoken words")
    overrides = beat.get("pronunciations", {})
    if not isinstance(overrides, dict):
        raise StudioError(f"Beat {index} pronunciations must be an object")
    normalized = {}
    for display, spoken in overrides.items():
        if not isinstance(display, str) or not key(display) or len(display.split()) != 1:
            raise StudioError(f"Beat {index} pronunciation keys must be single display words")
        normalized_key = key(display)
        if normalized_key in normalized:
            raise StudioError(f"Beat {index} has duplicate pronunciation keys")
        spoken = _text(spoken, f"Beat {index} pronunciation for {display}")
        if not key(spoken):
            raise StudioError(f"Beat {index} pronunciation for {display} must contain spoken words")
        normalized[normalized_key] = spoken
    available = {key(token) for token in tokens}
    unused = set(normalized) - available
    if unused:
        raise StudioError(f"Beat {index} pronunciation does not match a display word: {', '.join(sorted(unused))}")
    return [(token, normalized.get(key(token), token)) for token in tokens]


def align(beats, words):
    """Map provider boundaries to script tokens without substituting provider text."""
    if not isinstance(words, list) or not words:
        raise StudioError("Narration has no word timestamps")
    for word in words:
        if not isinstance(word, dict) or not isinstance(word.get("text"), str):
            raise StudioError("Narration word timestamps are invalid")
        start, end = word.get("start"), word.get("end")
        if (isinstance(start, bool) or isinstance(end, bool)
                or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end):
            raise StudioError("Narration word timestamps are invalid")
    if any(words[i]["start"] >= words[i + 1]["start"] or words[i]["end"] > words[i + 1]["end"]
           for i in range(len(words) - 1)):
        raise StudioError("Narration word timestamps must be ordered")
    result, cursor = [], 0
    for i, beat in enumerate(beats, 1):
        aligned = []
        for display, spoken in speech_parts(beat, i):
            target, matched, taken = key(spoken), "", []
            while cursor < len(words) and len(matched) < len(target):
                word = words[cursor]
                matched += key(word["text"])
                taken.append(word)
                cursor += 1
            if matched != target or not taken:
                raise StudioError(
                    f"Narration timing does not match beat {i} word '{display}'; "
                    "adjust its pronunciation or script, then regenerate"
                )
            aligned.append({"text": display, "start": taken[0]["start"], "end": taken[-1]["end"]})
        result.append(aligned)
    if cursor != len(words):
        raise StudioError("Narration returned extra words after the last beat")
    return result


def timing(beat_words, tail):
    starts = [0.0] + [max(0.0, words[0]["start"] - 0.12) for words in beat_words[1:]]
    ends = starts[1:] + [beat_words[-1][-1]["end"] + tail]
    return [(round(s, 3), round(e, 3)) for s, e in zip(starts, ends)]


def keyword_span(words, keyword, index):
    target = key(keyword)
    for i in range(len(words)):
        joined = ""
        for j in range(i, len(words)):
            joined += key(words[j]["text"])
            if joined == target:
                return i, j
            if not target.startswith(joined):
                break
    raise StudioError(f"Beat {index} keyword '{keyword}' must match whole spoken words in its say text")


def cue_time(words, cue, index):
    target = key(cue)
    for word in words:
        if key(word["text"]).startswith(target):
            return word["start"]
    raise StudioError(f"Beat {index} cue '{cue}' is not a spoken word in that beat")


def caption_size(words):
    chars = sum(len(w["text"]) for w in words) + len(words)
    return 78 if chars <= 22 else 70 if chars <= 34 else 62 if chars <= 46 else 56


def anim(*specs):
    return escape(";".join(s for s in specs if s), quote=True)


class Beat:
    """Builds one beat's stage markup and collects the sound effects it triggers."""

    def __init__(self, index, beat, words, start, end, brand, assets):
        self.i, self.beat, self.words, self.s, self.e = index, beat, words, start, end
        self.brand, self.assets, self.sounds = brand, assets, []
        self.visual_events = [start]
        self.first = index == 1

    def enter(self, preset, at, sound=None):
        if self.first and at < 0.3:
            return ""
        if sound:
            self.sounds.append((round(at, 3), sound))
        return f"{preset}@{at:.3f}"

    def slots(self, entries, earliest):
        """Reveal time for each entry: its cue word when given, else spread across the spoken part."""
        spoken_end = self.words[-1]["end"] if self.words else self.e
        span = max(0.4, min(spoken_end, self.e - 0.4) - earliest)
        times = []
        for n, entry in enumerate(entries):
            cue = entry.get("cue") if isinstance(entry, dict) else None
            times.append(cue_time(self.words, cue, self.i) if cue else earliest + span * n / max(1, len(entries)))
        return times

    def html(self):
        visual = self.beat["visual"]
        return getattr(self, "v_" + visual["type"])(visual, self.s + 0.08)

    def v_photo(self, v, t):
        src = self.assets[self.i]
        stamp = ""
        if v.get("stamp"):
            at = cue_time(self.words, v["stamp_cue"], self.i) if v.get("stamp_cue") else t + 0.6
            self.visual_events.append(at)
            self.sounds.append((round(at, 3), "stamp"))
            stamp = f'<div class="stamp" data-anim="{anim(f"stamp@{at:.3f}")}">{escape(v["stamp"])}</div>'
        credit = f'<div class="credit mono">{escape(v["credit"])}</div>' if v.get("credit") else ""
        return (f'<div class="photo" data-anim="{anim(self.enter("rise", t, "pop"))}"><div class="frame">'
                f'<img src="{src}" alt=""></div>{stamp}{credit}</div>')

    def v_card(self, v, t):
        lines = v.get("lines", [])
        lines = [line if isinstance(line, dict) else {"text": line} for line in lines]
        times = self.slots(lines, t + 0.5)
        rows = []
        for line, at in zip(lines, times):
            self.visual_events.append(at)
            self.sounds.append((round(at, 3), "tick"))
            tag = f'<span class="tag mono">{escape(line["tag"])}</span>' if line.get("tag") else ""
            rows.append(f'<div class="line" data-anim="{anim(f"rise@{at:.3f}")}">{tag}{escape(line["text"])}</div>')
        chip = ""
        if v.get("chip"):
            at = t + 0.7
            chip = (f'<span class="chip mono" data-anim="{anim(f"pop@{at:.3f}", f"pulse@{at + 0.6:.3f}:{max(0.8, self.e - at - 1):.2f}")}">'
                    f'{escape(v["chip"])}</span>')
        eyebrow = f'<div class="eyebrow mono">{escape(v["eyebrow"])}{chip}</div>' if v.get("eyebrow") or chip else ""
        latin = " latin" if v.get("latin") else ""
        rule = f'<div class="rule" data-anim="{anim(f"drawx@{t + 0.3:.3f}:0.5")}"></div>' if lines else ""
        return (f'<div class="card" data-anim="{anim(self.enter("pop", t, "pop"))}">{eyebrow}'
                f'<div class="title{latin}">{escape(v["title"])}</div>{rule}{"".join(rows)}</div>')

    def person(self, p, at, highlight_at=None):
        initials = p.get("initials") or "".join(part[0] for part in p["name"].split()[:2]).upper()
        c = self.brand["colors"]
        if highlight_at is None:
            role = f'<span class="role" style="background:{c["line"]}">{escape(p["role"])}</span>'
        else:
            self.sounds.append((round(highlight_at, 3), "pop"))
            role = (f'<span class="role" data-from="{c["line"]}" data-to="{c["accent"]}" data-ink-from="{c["ink"]}" '
                    f'data-ink-to="{c["on_accent"]}" style="background:{c["line"]}" '
                    f'data-anim="{anim(f"paint@{highlight_at:.3f}")}">{escape(p["role"])}</span>')
        return (f'<div class="person" data-anim="{anim(self.enter("rise", at, "pop"))}"><div class="avatar">{escape(initials)}</div>'
                f'<div><div class="name">{escape(p["name"])}</div>{role}</div></div>')

    def v_swap(self, v, t):
        second = cue_time(self.words, v["cue"], self.i) if v.get("cue") else t + max(0.6, (self.e - t) * 0.4)
        self.visual_events.append(second)
        self.sounds.append((round(second - 0.25, 3), "tick"))
        arrow = f'<div class="arrow" data-anim="{anim(f"drawy@{second - 0.25:.3f}:0.3")}"></div>'
        return self.person(v["from"], t) + arrow + self.person(v["to"], second, second + 0.35)

    def v_counter(self, v, t):
        label = f'<div class="counter-label" data-anim="{anim(self.enter("rise", t + 0.3))}">{escape(v.get("label", ""))}</div>'
        self.sounds.append((round(t, 3), "pop"))
        return (f'<div class="counter serif" data-from="{int(v.get("from", 0))}" data-to="{v["to"]}" '
                f'data-prefix="{escape(v.get("prefix", ""))}" data-suffix="{escape(v.get("suffix", ""))}" '
                f'data-anim="{anim(self.enter("pop", t), f"count@{t:.3f}:0.9")}">{v["to"]}</div>{label}')

    def v_stamp(self, v, t):
        at = cue_time(self.words, v["cue"], self.i) if v.get("cue") else t + 0.5
        self.visual_events.append(at)
        self.sounds.append((round(at, 3), "stamp"))
        title = f'<div class="title" style="text-align:center">{escape(v["title"])}</div>' if v.get("title") else ""
        eyebrow = f'<div class="eyebrow mono">{escape(v["eyebrow"])}</div>' if v.get("eyebrow") else ""
        head = f'<div data-anim="{anim(self.enter("rise", t, "pop"))}" style="text-align:center">{eyebrow}{title}</div>' if title or eyebrow else ""
        return head + f'<div class="stamp big" data-anim="{anim(f"stamp@{at:.3f}")}">{escape(v["text"])}</div>'

    def v_checklist(self, v, t):
        items = _items(v, "checklist")
        rows = []
        for item, at in zip(items, self.slots(items, t + 0.25)):
            self.visual_events.append(at)
            self.sounds.append((round(at + 0.15, 3), "tick"))
            rows.append(f'<div class="row" data-anim="{anim(f"rise@{at:.3f}")}"><div class="box">'
                        f'<i data-anim="{anim(f"tick@{at + 0.15:.3f}")}">✓</i></div>'
                        f'<div class="text">{escape(item["text"])}</div></div>')
        return f'<div class="card">{"".join(rows)}</div>'

    def v_list(self, v, t):
        items = _items(v, "list")
        rows = []
        for n, (item, at) in enumerate(zip(items, self.slots(items, t + 0.25)), 1):
            self.visual_events.append(at)
            self.sounds.append((round(at, 3), "pop"))
            rows.append(f'<div class="row" data-anim="{anim(f"rise@{at:.3f}")}"><div class="idx serif">{n}</div>'
                        f'<div class="text">{escape(item["text"])}</div></div>')
        return f'<div class="card">{"".join(rows)}</div>'

    def v_timeline(self, v, t):
        items = _items(v, "timeline", 2, 4)
        nodes = []
        for item, at in zip(items, self.slots(items, t + 0.35)):
            self.visual_events.append(at)
            self.sounds.append((round(at, 3), "tick"))
            chip = f'<span class="chip mono">{escape(item["chip"])}</span>' if item.get("chip") else ""
            nodes.append(f'<div class="node{" live" if item.get("live") else ""}" data-anim="{anim(f"rise@{at:.3f}")}">'
                         f'<div class="dot"></div><div class="when mono">{escape(str(item.get("when", "")))}</div>'
                         f'<div class="what">{escape(item["what"])}{chip}</div></div>')
        return (f'<div class="tl"><div class="rail" data-anim="{anim(f"drawy@{t:.3f}:{max(0.6, (self.e - t) * 0.5):.2f}")}"></div>'
                f'{"".join(nodes)}</div>')

    def v_outro(self, v, t):
        b, c = self.brand, self.brand["colors"]
        keyword = v.get("comment_keyword") or self.beat["keyword"]
        self.sounds += [(round(t, 3), "chime"), (round(t + 0.5, 3), "pop"), (round(t + 1.6, 3), "pop")]
        follow_at = t + 1.6
        type_at = t + 0.8
        self.sounds += [(round(type_at + n * 0.12, 3), "tick") for n in range(min(4, len(keyword)))]
        pulse = max(0.8, self.e - follow_at - 0.9)
        return (
            f'<div class="outro"><div class="logo" data-anim="{anim(f"pop@{t:.3f}")}"><div class="tile">{escape(b["mark"])}</div>'
            f'<div><div class="name">{escape(b["name"])}</div><div class="tagline">{escape(b["tagline"])}</div></div></div>'
            f'<div class="comment" data-anim="{anim(f"rise@{t + 0.5:.3f}")}"><div class="avatar">{escape(b["mark"])}</div>'
            f'<div><div class="prompt">{escape(b["outro"].get("comment_prompt", "Comment"))}</div>'
            f'<div class="typed" data-text="{escape(keyword)}" data-anim="{anim(f"type@{type_at:.3f}:0.6")}"></div></div></div>'
            f'<div data-anim="{anim(f"pop@{follow_at:.3f}")}"><div class="follow" data-from="{c["card"]}" data-to="{c["accent"]}" '
            f'data-ink-from="{c["ink"]}" data-ink-to="{c["on_accent"]}" style="background:{c["card"]}" '
            f'data-anim="{anim(f"paint@{follow_at + 0.5:.3f}", f"pulse@{follow_at + 0.9:.3f}:{pulse:.2f}")}">'
            f'{escape(b["outro"].get("follow", "Follow"))}</div></div>'
            f'<div class="handle mono" data-anim="{anim(f"fade@{follow_at:.3f}:0.4")}">{escape(b["handle"])}</div></div>'
        )


def caption(index, beat, words, start, end, brand, last):
    lo, hi = keyword_span(words, beat["keyword"], index)
    c = brand["colors"]
    spans = []
    group = []
    for n, word in enumerate(words):
        at = 0.0 if index == 1 and n == 0 else word["start"]
        text = escape(word["text"])
        if lo <= n <= hi:
            group.append(f'<span class="w kw" data-anim="{anim(f"word@{at:.3f}")}"><i class="mk" data-anim="{anim(f"marker@{at:.3f}")}"></i>'
                         f'<b data-from="{c["ink"]}" data-to="{c["on_accent"]}" data-anim="{anim(f"ink@{at:.3f}")}">{text}</b></span>')
            if n == hi:
                spans.append(f'<span class="kwg">{"".join(group)}</span>')
        else:
            spans.append(f'<span class="w" data-anim="{anim(f"word@{at:.3f}")}"><b>{text}</b></span>')
    exit_ = "" if last else f"out@{end - 0.2:.3f}"
    return (f'<div class="cap" style="--cap-size:{caption_size(words)}px" data-anim="{anim(exit_)}">'
            f'{"".join(spans)}</div>')


def header(config, times, duration):
    beats, b = config["beats"], config["_brand"]
    steps = [(n, beat["step"], s, e) for n, (beat, (s, e)) in enumerate(zip(beats, times)) if "step" in beat]
    topic_anim = ""
    overlays = []
    if steps:
        total = max(step for _, step, _, _ in steps)
        first = steps[0][2]
        last = steps[-1][3]
        topic_anim = anim(f"hide@{first:.3f}", f"show@{last:.3f}")
        label = config.get("steps", {}).get("label", "")
        for n, step, s, e in steps:
            if n + 1 < len(beats) and beats[n + 1].get("step") == step:
                continue
            start = min(ss for _, st, ss, _ in steps if st == step)
            segs = []
            for k in range(1, total + 1):
                if k < step:
                    segs.append('<span class="seg"><i></i></span>')
                elif k == step:
                    segs.append(f'<span class="seg"><i data-anim="{anim(f"fill@{start + 0.1:.3f}:0.5")}"></i></span>')
                else:
                    segs.append('<span class="seg"><i style="transform:scaleX(0)"></i></span>')
            title = next((bt.get("step_title") for bt in beats if bt.get("step") == step and bt.get("step_title")), label)
            overlays.append(
                f'<div class="steps" style="opacity:0" data-anim="{anim(f"show@{start:.3f}", f"hide@{e:.3f}")}">'
                f'<span class="num serif">{step}</span><span class="of mono">/{total}</span>'
                f'<span class="label">{escape(title)}</span>{"".join(segs)}</div>')
    return (f'<div class="hdr"><div class="mark">{escape(b["mark"])}</div>'
            f'<div class="topic" data-anim="{topic_anim}">{escape(config["topic"])}</div>{"".join(overlays)}</div>'
            f'<div class="track"><i data-anim="{anim(f"fill@0:{duration:.3f}")}"></i></div>')


def composition(config, beat_words, times, assets):
    brand = config["_brand"]
    duration = times[-1][1]
    clips, sounds, visual_events = [], [], []
    for index, (beat, words, (s, e)) in enumerate(zip(config["beats"], beat_words, times), 1):
        last = index == len(times)
        builder = Beat(index, beat, words, s, e, brand, assets)
        stage = builder.html()
        sounds += builder.sounds
        visual_events.append(builder.visual_events)
        if index > 1:
            sounds.append((round(max(0, s - 0.1), 3), "whoosh"))
        exit_ = "" if last else f"out@{e - 0.2:.3f}"
        clips.append(
            f'<div class="clip beat" id="beat-{index}" data-start="{s:.3f}" data-duration="{e - s:.3f}" data-track-index="{index % 2 + 1}">'
            f'{caption(index, beat, words, s, e, brand, last)}'
            f'<div class="stage" data-anim="{anim(exit_)}"><div class="float" data-anim="{anim(f"float@{s:.3f}:{e - s:.3f}")}">{stage}</div></div></div>')
    variables = "".join(f"--{k.replace('_', '-')}:{v};" for k, v in brand["colors"].items())
    page = f"""<!doctype html>
<html lang="ne"><head><meta charset="utf-8"><title>{escape(config["title"])}</title>
<style>{(ASSETS / "reel.css").read_text(encoding="utf-8")}
:root{{{variables}}}</style></head>
<body><div id="main" data-composition-id="main" data-width="{WIDTH}" data-height="{HEIGHT}" data-duration="{duration:.3f}">
{header(config, times, duration)}
{"".join(clips)}
</div>
<script src="assets/gsap.min.js"></script><script src="assets/reel.js"></script>
</body></html>
"""
    return page, sounds, visual_events


def file_hash(*parts):
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part if isinstance(part, bytes) else str(part).encode("utf-8"))
    return digest.hexdigest()[:16]


def narrate(config, cache):
    from .speech import synthesize
    voice = config["voice"]
    script = " ".join(spoken for index, beat in enumerate(config["beats"], 1)
                      for _, spoken in speech_parts(beat, index))
    stem = "voice-" + file_hash(script, voice["name"], voice["rate"], voice["pitch"])
    audio, words_path = cache / f"{stem}.mp3", cache / f"{stem}.json"
    if not (audio.is_file() and words_path.is_file()):
        partial = cache / f"{stem}.partial.mp3"
        words = asyncio.run(synthesize(script, voice["name"], partial, voice["rate"], voice["pitch"]))
        os.replace(partial, audio)
        words_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return audio, json.loads(words_path.read_text(encoding="utf-8"))


def collect_images(config, project_dir, cache, assets_dir):
    paths = {}
    for index, beat in enumerate(config["beats"], 1):
        v = beat["visual"]
        if v["type"] != "photo":
            continue
        if v.get("src"):
            source = (project_dir / v["src"]).resolve()
            if not source.is_file():
                raise StudioError(f"Beat {index} photo not found: {source}")
        else:
            source = cache / ("img-" + file_hash(v["url"]) + Path(v["url"].split("?")[0]).suffix.lower()[:5])
            if not source.is_file():
                source.write_bytes(request_bytes(v["url"], {"User-Agent": "KathaStudio/1.0 (reel builder)"}))
        name = f"photo-{index}{source.suffix or '.jpg'}"
        shutil.copyfile(source, assets_dir / name)
        paths[index] = f"assets/{name}"
    return paths


def build(project_path, config, work_dir):
    gsap = REPO / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    if not gsap.is_file():
        raise StudioError("GSAP is missing; run npm install in the repository root")
    cache = work_dir / "cache"
    build_dir = work_dir / "composition"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    assets_dir = build_dir / "assets"
    (assets_dir / "fonts").mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)
    for font in config["_brand"]["_fonts"].glob("*.ttf"):
        shutil.copyfile(font, assets_dir / "fonts" / font.name)
    for name in ("reel.js",):
        shutil.copyfile(ASSETS / name, assets_dir / name)
    shutil.copyfile(gsap, assets_dir / "gsap.min.js")
    voice, words = narrate(config, cache)
    beat_words = align(config["beats"], words)
    times = timing(beat_words, config["outro"]["tail"])
    images = collect_images(config, project_path.parent, cache, assets_dir)
    page, sounds, visual_events = composition(config, beat_words, times, images)
    (build_dir / "index.html").write_text(page, encoding="utf-8")
    return voice, words, beat_words, times, sounds, visual_events


def visual_pacing(times, visual_events):
    """Measure gaps between planned story-content reveals, excluding the closing outro."""
    if len(times) != len(visual_events):
        raise StudioError("Visual pacing plan does not match the beat timeline")
    checks = []
    for index, ((start, end), events) in enumerate(zip(times[:-1], visual_events[:-1]), 1):
        if not events or any(not math.isfinite(at) or at < start or at >= end for at in events):
            raise StudioError(f"Beat {index} has a visual reveal outside its time window")
        boundaries = sorted(set([start, end] + events))
        gap = round(max(b - a for a, b in zip(boundaries, boundaries[1:])), 3)
        checks.append({"check": f"beat_{index}_visual_gap_seconds", "value": gap,
                       "limit": f"<= {LIMITS['visual_gap']}", "pass": gap <= LIMITS["visual_gap"]})
    return checks


def hyperframes():
    local = REPO / "node_modules" / ".bin" / ("hyperframes.cmd" if os.name == "nt" else "hyperframes")
    if local.is_file():
        return [str(local)]
    found = shutil.which("hyperframes")
    if not found:
        raise StudioError("HyperFrames not found; run npm install in the repository root")
    return [found]


def tool(name):
    path = shutil.which(name)
    if not path:
        raise StudioError(f"{name} not found on PATH")
    return path


def execute(args, cwd=None, env=None, capture=False):
    try:
        return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=capture,
                              text=capture, encoding="utf-8" if capture else None, errors="replace" if capture else None)
    except FileNotFoundError as exc:
        raise StudioError(f"Executable not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "")[-1500:] if capture else ""
        raise StudioError(f"{Path(args[0]).name} failed with exit code {exc.returncode}. {detail}".strip()) from exc


def render_video(build_dir, output):
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", HYPERFRAMES_NO_UPDATE_CHECK="1", HYPERFRAMES_NO_ORPHAN_CLEANUP="1")
    execute(hyperframes() + ["render", str(build_dir), "-o", str(output), "--fps", str(FPS), "-q", "delivery",
                             "--strict", "--quiet", "--no-best-effort"], cwd=str(REPO), env=env)
    if not output.is_file() or not output.stat().st_size:
        raise StudioError("HyperFrames did not produce a video")


def mix(silent, voice, music_wav, sfx_wav, volume, duration, output):
    graph = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v1][v2];"
             f"[2:a]volume={volume}[m];[m][v2]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[duck];"
             f"[v1][duck][3:a]amix=inputs=3:normalize=0:duration=longest,"
             f"loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,"
             f"alimiter=limit=0.668:attack=2:release=50:level=disabled[a]")
    execute([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent), "-i", str(voice),
             "-i", str(music_wav), "-i", str(sfx_wav), "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(output)])


def loudness(path):
    result = execute([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af",
                      "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture=True)
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", result.stderr)
    if not match:
        raise StudioError("Could not measure loudness")
    data = json.loads(match.group(0))
    return float(data["input_i"]), float(data["input_tp"])


def raw_output(args):
    try:
        return subprocess.run(args, capture_output=True, check=True).stdout
    except FileNotFoundError as exc:
        raise StudioError(f"Executable not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", "replace")[-800:]
        raise StudioError(f"{Path(args[0]).name} failed with exit code {exc.returncode}. {detail}".strip()) from exc


def gray_frames(path, fps, width, height):
    import numpy as np
    data = raw_output([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf",
                       f"fps={fps},scale={width}:{height},format=gray", "-f", "rawvideo", "-"])
    return np.frombuffer(data, dtype=np.uint8).reshape(-1, height, width).astype(np.float32)


def motion_metrics(frames, step):
    import numpy as np
    diffs = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    longest = run = 0
    for value in diffs:
        run = run + 1 if value < 0.5 else 0
        longest = max(longest, run)
    return {"moving_share": round(float((diffs > 1.0).mean()), 3), "max_hold": round(longest * step, 2),
            "mean_change": round(float(diffs.mean()), 2)}


def frame_at(path, seconds):
    import numpy as np
    data = raw_output([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-ss", f"{seconds:.3f}", "-i", str(path),
                       "-frames:v", "1", "-vf", "format=rgb24", "-f", "rawvideo", "-"])
    return np.frombuffer(data, dtype=np.uint8).reshape(HEIGHT, WIDTH, 3).astype(np.int16)


def outside_ink(frame, paper, box=TEXT_BOX):
    import numpy as np
    distance = np.abs(frame - np.array(paper, dtype=np.int16)).max(axis=2) > 60
    x0, y0, x1, y1 = box
    distance[y0:y1, x0:x1] = False
    return int(distance.sum())


def hex_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def quality(video, config, words, beat_words, times, visual_events):
    duration = times[-1][1]
    spoken = words[-1]["end"] - words[0]["start"]
    checks = visual_pacing(times, visual_events)

    def check(name, value, ok, limit):
        checks.append({"check": name, "value": value, "limit": limit, "pass": bool(ok)})

    lo, hi = LIMITS["duration"]
    check("duration_seconds", round(duration, 2), lo <= duration <= hi, f"{lo}-{hi}")
    rate = len(words) / spoken
    lo, hi = LIMITS["words_per_second"]
    check("words_per_second", round(rate, 2), lo <= rate <= hi, f"{lo}-{hi}")
    for n, ((s, e), bw) in enumerate(zip(times, beat_words), 1):
        lo, hi = LIMITS["outro_seconds" if n == len(times) else "beat_seconds"]
        check(f"beat_{n}_seconds", round(e - s, 2), lo <= e - s <= hi, f"{lo}-{hi}")
        check(f"beat_{n}_words", len(bw), len(bw) <= LIMITS["beat_words"], f"<= {LIMITS['beat_words']}")
    lufs, peak = loudness(video)
    lo, hi = LIMITS["lufs"]
    check("integrated_lufs", lufs, lo <= lufs <= hi, f"{lo} to {hi}")
    check("true_peak_dbtp", peak, peak <= LIMITS["true_peak"], f"<= {LIMITS['true_peak']}")
    motion = motion_metrics(gray_frames(video, 4, 180, 320), 0.25)
    check("moving_share", motion["moving_share"], motion["moving_share"] >= LIMITS["moving_share"], f">= {LIMITS['moving_share']}")
    check("longest_static_hold_seconds", motion["max_hold"], motion["max_hold"] <= LIMITS["max_hold"], f"<= {LIMITS['max_hold']}")
    paper = hex_rgb(config["_brand"]["colors"]["paper"])
    worst = 0
    for s, e in times:
        for at in (s + (e - s) * 0.55, e - 0.3):
            worst = max(worst, outside_ink(frame_at(video, min(at, duration - 0.05)), paper))
    check("pixels_outside_text_box", worst, worst <= 200, "<= 200")
    return {"passed": all(c["pass"] for c in checks), "mean_frame_change": motion["mean_change"], "checks": checks}


def storyboard_image(video, times, image):
    with tempfile.TemporaryDirectory(prefix="katha-board-") as temp:
        for n, (s, e) in enumerate(times, 1):
            execute([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{min(e - 0.3, s + (e - s) * 0.7):.3f}",
                     "-i", str(video), "-frames:v", "1", "-vf", "scale=270:480", str(Path(temp) / f"f{n:03d}.png")])
        columns = min(6, len(times))
        rows = math.ceil(len(times) / columns)
        execute([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-framerate", "1", "-i", str(Path(temp) / "f%03d.png"),
                 "-vf", f"tile={columns}x{rows}:padding=8:margin=8:color=white", "-frames:v", "1", str(image)])
def storyboard_plan(config, times, visual_events, markdown):
    def cell(value):
        return str(value).replace("|", r"\|").replace("\n", " ")

    lines = [f"# Storyboard: {config['title']}", "",
             "| # | Time | Visual | Reveals (s) | Keyword | Caption | Pronunciation |",
             "|---|---|---|---|---|---|---|"]
    for n, (beat, (s, e), events) in enumerate(zip(config["beats"], times, visual_events), 1):
        reveals = ", ".join(f"{at:.1f}" for at in sorted(set(events)))
        spoken = " ".join(spoken for _, spoken in speech_parts(beat, n))
        lines.append(f"| {n} | {s:.1f}-{e:.1f}s | {cell(beat['visual']['type'])} | {reveals} | "
                     f"{cell(beat['keyword'])} | {cell(beat['say'])} | {cell(spoken)} |")
    sources = config.get("sources", [])
    if sources:
        lines += ["", "## Sources"] + [f"- {source}" for source in sources]
    credits = [b["visual"]["credit"] for b in config["beats"] if b["visual"].get("credit")]
    if credits:
        lines += ["", "## Credits"] + [f"- {credit}" for credit in credits]
    markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")


def project_fingerprint(path, config):
    brand_file = json.dumps({k: v for k, v in config["_brand"].items() if not k.startswith("_")}, sort_keys=True, ensure_ascii=False)
    code = [Path(__file__).read_bytes(), (Path(__file__).parent / "speech.py").read_bytes(),
            (Path(__file__).parent / "sound.py").read_bytes(),
            (ASSETS / "reel.js").read_bytes(), (ASSETS / "reel.css").read_bytes()]
    return file_hash(Path(path).read_bytes(), brand_file, *code)


def preview_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reel(project, approval=None):
    path, config = load_reel(project)
    root, stem = path.parent, path.stem
    out_dir = root / "output"
    preview, qa_path = out_dir / f"{stem}.mp4", out_dir / f"{stem}-qa.json"
    fingerprint = project_fingerprint(path, config)
    if approval is not None:
        if approval != FINAL_EXPORT_APPROVAL:
            raise StudioError(f'Export needs the exact approval "{FINAL_EXPORT_APPROVAL}"')
        try:
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StudioError("No reviewed preview found; run the reel command without --approval first") from exc
        if qa.get("fingerprint") != fingerprint or not preview.is_file():
            raise StudioError("Project changed since the preview; render and review it again before export")
        if not qa.get("passed"):
            raise StudioError("Preview failed quality checks; fix them before export")
        if qa.get("preview_sha256") != preview_hash(preview):
            raise StudioError("Preview changed since the quality checks; render and review it again before export")
        exports = root / "Exports"
        exports.mkdir(exist_ok=True)
        shutil.copyfile(preview, exports / f"{stem}.mp4")
        print(f"Exported {exports / f'{stem}.mp4'}")
        return 0
    from . import sound
    build_dir = root / ".katha" / stem
    build_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(exist_ok=True)
    qa_path.unlink(missing_ok=True)
    print("Building composition and narration...")
    voice, words, beat_words, times, sounds, visual_events = build(path, config, build_dir)
    duration = times[-1][1]
    voice_duration = audio_duration(voice)
    if words[-1]["end"] > voice_duration + 0.1:
        raise StudioError("Narration word timestamps exceed audio duration")
    if voice_duration > duration:
        raise StudioError("Narration is longer than the composition")
    plan_path = out_dir / f"{stem}-storyboard.md"
    storyboard_plan(config, times, visual_events, plan_path)
    print(f"Storyboard plan: {plan_path}")
    pacing = visual_pacing(times, visual_events)
    failed_pacing = [c for c in pacing if not c["pass"]]
    if failed_pacing:
        detail = ", ".join(f"{c['check']}: {c['value']}s" for c in failed_pacing)
        raise StudioError(f"Story-content reveal gap exceeds {LIMITS['visual_gap']}s: {detail}; split or add cued content")
    print(f"Rendering {duration:.1f}s with HyperFrames...")
    silent = build_dir / "silent.mp4"
    render_video(build_dir / "composition", silent)
    music = config["music"]
    sound.write_wav(build_dir / "music.wav", sound.music_bed(duration, music["bpm"], music["seed"]))
    sound.write_wav(build_dir / "sfx.wav", sound.sfx_track(duration, sounds))
    mix(silent, voice, build_dir / "music.wav", build_dir / "sfx.wav", music["volume"], duration, preview)
    print("Running quality checks...")
    qa = quality(preview, config, words, beat_words, times, visual_events)
    qa["fingerprint"] = fingerprint
    qa["preview_sha256"] = preview_hash(preview)
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    storyboard_image(preview, times, out_dir / f"{stem}-storyboard.jpg")
    failed = [c for c in qa["checks"] if not c["pass"]]
    for c in failed:
        print(f"QA FAIL {c['check']}: {c['value']} (limit {c['limit']})")
    print(f"Preview: {preview}\nStoryboard: {out_dir / f'{stem}-storyboard.jpg'}")
    if failed:
        raise StudioError(f"{len(failed)} quality check(s) failed; see {qa_path}")
    print(f'All quality checks passed. Review, then export with --approval "{FINAL_EXPORT_APPROVAL}".')
    return 0

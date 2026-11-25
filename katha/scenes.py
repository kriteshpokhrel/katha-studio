"""Validated, local-media SVG scenes with persistent objects and narration-cued actions."""
from html import escape
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

from .studio import StudioError

KINDS = {"group", "circle", "ellipse", "rect", "line", "path", "text", "image", "video", "phase"}
GEOMETRY = {"cx", "cy", "r", "rx", "ry", "width", "height", "x1", "x2", "y1", "y2",
            "stroke-width", "font-size", "rx", "ry"}
PAINT = {"fill", "stroke"}
STATE = {"x", "y", "rotation", "scale", "opacity", "angle", "phase", "draw"}
ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
COLOR = re.compile(r"#[0-9a-fA-F]{6}|none|paper|dot|ink|muted|line|card|accent|on_accent")
REQUIRED = {"circle": {"r"}, "ellipse": {"rx", "ry"}, "rect": {"width", "height"},
            "line": {"x1", "y1", "x2", "y2"}, "path": {"d"},
            "image": {"width", "height"}, "video": {"width", "height"}}


def fail(message):
    raise StudioError(f"Scene: {message}")


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be non-empty text")
    return value


def number(value, label, low=-10000, high=10000):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        fail(f"{label} must be a finite number in {low}..{high}")
    return value


def color(value):
    if not isinstance(value, str) or not COLOR.fullmatch(value):
        fail(f"invalid color {value!r}; use a brand token, none or #RRGGBB")
    return value


def objects(scene):
    result = {}

    def walk(nodes):
        if not isinstance(nodes, list) or not nodes:
            fail("objects/children must be a non-empty list")
        for node in nodes:
            if not isinstance(node, dict):
                fail("object must be an object")
            ident, kind = node.get("id"), node.get("type")
            if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in result:
                fail(f"invalid or duplicate object id {ident!r}")
            if not isinstance(kind, str) or kind not in KINDS:
                fail(f"unknown object type {kind!r}")
            if set(node) - (STATE | {"id", "type", "attrs", "text", "asset", "orbit", "clip", "children"}):
                fail(f"{ident} has unsupported object fields")
            result[ident] = node
            if len(result) > 100:
                fail("a scene may contain at most 100 objects")
            for name in STATE:
                if name in node:
                    number(node[name], f"{ident}.{name}")
            for name in ("opacity", "draw"):
                if name in node:
                    number(node[name], f"{ident}.{name}", 0, 1)
            if "scale" in node:
                number(node["scale"], f"{ident}.scale", 0.01, 10)
            attrs = node.get("attrs", {})
            if not isinstance(attrs, dict):
                fail(f"{ident}.attrs must be an object")
            if REQUIRED.get(kind, set()) - set(attrs):
                fail(f"{ident} needs geometry: {', '.join(sorted(REQUIRED[kind]))}")
            for name, value in attrs.items():
                if name in GEOMETRY:
                    number(value, f"{ident}.{name}", 0, 2000)
                elif name in PAINT:
                    color(value)
                elif name == "d" and kind == "path":
                    if not isinstance(value, str) or not re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz0-9eE., +\-]+", value):
                        fail(f"{ident} has an invalid path")
                elif name == "text-anchor" and value in ("start", "middle", "end"):
                    pass
                else:
                    fail(f"unsupported attribute {ident}.{name}")
            if kind == "text":
                text(node.get("text"), f"{ident}.text")
            if kind in ("image", "video"):
                text(node.get("asset"), f"{ident}.asset")
            if kind != "group" and "children" in node:
                fail(f"{ident}: only groups can have children")
            if "orbit" in node:
                orbit = node["orbit"]
                if not isinstance(orbit, dict) or set(orbit) != {"cx", "cy", "rx", "ry"}:
                    fail(f"{ident}.orbit needs cx, cy, rx, ry")
                for name, value in orbit.items():
                    number(value, f"{ident}.orbit.{name}", 0, 768)
            if "clip" in node:
                clip = node["clip"]
                if not isinstance(clip, dict) or set(clip) != {"r"}:
                    fail(f"{ident}.clip needs a circle radius r")
                number(clip["r"], f"{ident}.clip.r", 1, 768)
            if kind == "group":
                walk(node.get("children"))
    walk(scene.get("objects"))
    return result


def has_picture(node):
    if node["type"] == "group":
        return any(has_picture(child) for child in node["children"])
    return node["type"] != "text"


def validate(config):
    assets, scenes = config.get("assets", {}), config.get("scenes", {})
    if not isinstance(assets, dict) or not isinstance(scenes, dict):
        fail("assets and scenes must be objects")
    extensions = {"image": {".png", ".jpg", ".jpeg", ".webp"},
                  "video": {".mp4"}, "audio": {".wav", ".mp3", ".m4a"}}
    for ident, asset in assets.items():
        if not isinstance(ident, str) or not ID.fullmatch(ident) or not isinstance(asset, dict):
            fail("invalid asset entry")
        kind = asset.get("kind")
        source = text(asset.get("src"), f"asset {ident}.src")
        if not isinstance(kind, str) or kind not in extensions or Path(source).suffix.lower() not in extensions[kind]:
            fail(f"asset {ident} has unsupported kind/extension")
        if asset.get("origin") not in ("original", "licensed", "generated"):
            fail(f"asset {ident} needs origin original, licensed or generated")
        for name in ("credit", "license"):
            text(asset.get(name), f"asset {ident}.{name}")
        if asset["origin"] != "original":
            text(asset.get("source"), f"asset {ident}.source")
        if asset["origin"] == "generated":
            for name in ("provider", "prompt", "cost"):
                text(asset.get(name), f"asset {ident}.{name}")
    indexes = {}
    for ident, scene in scenes.items():
        if not isinstance(ident, str) or not ID.fullmatch(ident) or not isinstance(scene, dict):
            fail("invalid scene entry")
        text(scene.get("description"), f"{ident}.description")
        indexes[ident] = objects(scene)
        for node in indexes[ident].values():
            if node["type"] in ("image", "video"):
                asset = assets.get(node["asset"])
                if not asset or asset["kind"] != node["type"]:
                    fail(f"{ident}.{node['id']} needs a matching asset")
    used, previous = set(), None
    for i, beat in enumerate(config["beats"], 1):
        visual = beat["visual"]
        if visual["type"] != "scene":
            previous = None
            continue
        ident = visual.get("scene")
        if not isinstance(ident, str) or ident not in indexes:
            fail(f"beat {i} references unknown scene {ident!r}")
        if ident in used and ident != previous:
            fail(f"scene {ident} must occupy consecutive beats")
        used.add(ident)
        previous = ident
        text(visual.get("purpose"), f"beat {i} visual.purpose")
        actions = visual.get("actions", [])
        if not isinstance(actions, list) or len(actions) > 30:
            fail(f"beat {i} actions must be a list of at most 30 entries")
        for action in actions:
            if (not isinstance(action, dict) or not isinstance(action.get("target"), str)
                    or action["target"] not in indexes[ident]):
                fail(f"beat {i} action references unknown target")
            if set(action) - {"target", "cue", "duration", "to", "meaning"}:
                fail(f"beat {i} action has unsupported fields")
            target = indexes[ident][action["target"]]
            text(action.get("meaning"), f"beat {i} action.meaning")
            number(action.get("duration", 0.5), f"beat {i} duration", 0.05, 6)
            if "cue" in action:
                text(action["cue"], f"beat {i} cue")
            destination = action.get("to")
            if not isinstance(destination, dict) or not destination or set(destination) - STATE:
                fail(f"beat {i} action.to needs supported numeric state fields")
            for name, value in destination.items():
                number(value, f"beat {i} to.{name}")
                if name in ("opacity", "draw"):
                    number(value, f"beat {i} to.{name}", 0, 1)
                if name == "scale":
                    number(value, f"beat {i} to.scale", 0.01, 10)
                if name == "phase" and target["type"] != "phase":
                    fail("phase animation needs a phase object")
                if name == "angle" and "orbit" not in target:
                    fail("angle animation needs an orbit")
                if name == "draw" and target["type"] not in ("path", "line", "circle", "ellipse", "rect"):
                    fail("draw animation needs a geometric shape")
    if set(scenes) - used:
        fail("remove unused scenes")


def local_files(config, root):
    return [(ident, (root / asset["src"]).resolve()) for ident, asset in config.get("assets", {}).items()]


def validate_media(config, ident, source, times):
    kind = config["assets"][ident]["kind"]
    ffprobe, ffmpeg = shutil.which("ffprobe"), shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        fail("FFmpeg and ffprobe are required to validate local media")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_type,width,height,duration:format=duration", "-of", "json", str(source)],
            capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        stream_kind = "audio" if kind == "audio" else "video"
        stream = next((s for s in metadata["streams"] if s.get("codec_type") == stream_kind), None)
        if stream is None:
            raise ValueError(f"no {stream_kind} stream")
        if kind != "audio" and (stream.get("width", 0) <= 0 or stream.get("height", 0) <= 0):
            raise ValueError("invalid image dimensions")
        if kind != "image":
            duration = float(stream.get("duration", metadata.get("format", {}).get("duration", 0)))
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError("invalid media duration")
            spans = {}
            for beat, (start, end) in zip(config["beats"], times):
                visual = beat["visual"]
                if visual["type"] == "scene":
                    spans.setdefault(visual["scene"], [start, end])[1] = end
            for scene, (start, end) in spans.items():
                uses_asset = any(n.get("asset") == ident for n in objects(config["scenes"][scene]).values())
                if kind == "video" and uses_asset and duration + 1 / 30 < end - start:
                    raise ValueError(f"video is {duration:.2f}s but scene {scene} needs {end - start:.2f}s; trim or extend it explicitly")
        decoded = subprocess.run(
            [ffmpeg, "-v", "error", "-xerror", "-i", str(source), "-map",
             "0:a:0" if kind == "audio" else "0:v:0", "-f", "null", "-"],
            capture_output=True, text=True, check=True)
        if decoded.stderr.strip():
            raise ValueError(decoded.stderr.strip())
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        fail(f"asset {ident} is not usable {kind} media: {exc}")


def collect(config, root, destination, times):
    paths = {}
    for ident, source in local_files(config, root):
        if not source.is_file():
            fail(f"asset {ident} not found: {source}; acquire it before rendering")
        validate_media(config, ident, source, times)
        if config["assets"][ident]["kind"] == "audio":
            continue
        name = f"media-{ident}{source.suffix.lower()}"
        shutil.copyfile(source, destination / name)
        paths[ident] = f"assets/{name}"
    return paths


def render(config, beat_words, times, assets, cue_time):
    """One DOM subtree per consecutive scene; all actions seek on the master timeline."""
    groups, schedules = {}, []
    events = {i: [s] for i, (s, _) in enumerate(times)}
    for i, (beat, words, (start, end)) in enumerate(zip(config["beats"], beat_words, times)):
        visual = beat["visual"]
        if visual["type"] != "scene":
            continue
        ident = visual["scene"]
        groups.setdefault(ident, [start, end])[1] = end
        nodes = objects(config["scenes"][ident])
        for action in visual.get("actions", []):
            at = cue_time(words, action["cue"], i + 1) if action.get("cue") else start
            duration = action.get("duration", 0.5)
            if at + duration > end + 0.001:
                fail(f"beat {i + 1} action {action['target']} exceeds its beat; shorten its duration")
            target_id = f"scene-{ident}-{action['target']}"
            for earlier in schedules:
                if earlier["target"] == target_id and set(earlier["to"]) & set(action["to"]):
                    if at < earlier["at"] + earlier["duration"] - 0.001:
                        fail(f"overlapping actions on {target_id}; use consecutive cues")
            schedules.append({"target": target_id, "at": at, "duration": duration, "to": action["to"]})
            # Only actual non-text object changes count; no caption/float/progress events.
            if has_picture(nodes[action["target"]]):
                steps = max(1, math.ceil(duration))
                events[i] += [round(at + duration * n / steps, 3) for n in range(steps + 1)
                              if at + duration * n / steps < end]
    palette = config["_brand"]["colors"]

    def paint(value):
        return palette.get(value, value)

    def node_html(node, prefix, start, end):
        kind = node["type"]
        ident = prefix + node["id"]
        attrs = {k: paint(v) if k in PAINT else v for k, v in node.get("attrs", {}).items()}
        state = {k: node[k] for k in STATE if k in node}
        if "orbit" in node:
            state["orbit"] = node["orbit"]
        data = escape(json.dumps(state), quote=True)
        clip = ""
        if "clip" in node:
            clip = f'<defs><clipPath id="{ident}-clip"><circle r="{node["clip"]["r"]}"/></clipPath></defs>'
        attr_text = " ".join(f'{k}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
        if kind == "group":
            body = "".join(node_html(child, prefix, start, end) for child in node["children"])
        elif kind == "phase":
            radius = attrs.get("r", 70)
            body = (f'<circle r="{radius}" fill="{palette["ink"]}"/>'
                    f'<path class="phase-light" fill="{palette["card"]}"/>'
                    f'<circle r="{radius}" fill="none" stroke="{palette["muted"]}" stroke-width="2"/>')
        elif kind == "image":
            body = f'<image href="{assets[node["asset"]]}" {attr_text} preserveAspectRatio="xMidYMid slice"/>'
        elif kind == "video":
            body = (f'<foreignObject width="{attrs.get("width", 400)}" height="{attrs.get("height", 300)}">'
                    f'<video id="{ident}-media" xmlns="http://www.w3.org/1999/xhtml" class="clip" src="{assets[node["asset"]]}" '
                    f'data-start="{start}" data-duration="{end - start}" data-volume="0" muted playsinline '
                    f'style="width:100%;height:100%;object-fit:cover"></video></foreignObject>')
        else:
            content = escape(node.get("text", "")) if kind == "text" else ""
            body = f'<{kind} {attr_text}>{content}</{kind}>'
        if clip:
            body = clip + f'<g clip-path="url(#{ident}-clip)">{body}</g>'
        return (f'<g id="{ident}" data-scene-state="{data}" data-kind="{kind}" '
                f'data-radius="{attrs.get("r", 70)}">{body}</g>')
    html = []
    for ident, (start, end) in groups.items():
        body = "".join(node_html(n, f"scene-{ident}-", start, end) for n in config["scenes"][ident]["objects"])
        html.append(f'<div class="scene-stage" data-scene-start="{start}" data-scene-duration="{end - start}">'
                    f'<svg viewBox="0 0 768 548" role="img" '
                    f'aria-label="{escape(config["scenes"][ident]["description"], quote=True)}">{body}</svg></div>')
    payload = json.dumps(schedules, ensure_ascii=True).replace("<", "\\u003c")
    return "".join(html), payload, events


def coverage(config, times):
    total = sum(e - s for s, e in times[:-1])
    pictorial, longest, run = 0, 0, 0
    for beat, (start, end) in zip(config["beats"][:-1], times[:-1]):
        v = beat["visual"]
        picture = v["type"] == "photo" or (
            v["type"] == "scene" and any(has_picture(n) for n in config["scenes"][v["scene"]]["objects"]))
        if picture:
            pictorial += end - start
            run = 0
        else:
            run += 1
            longest = max(longest, run)
    return round(pictorial / total, 3) if total else 0, longest

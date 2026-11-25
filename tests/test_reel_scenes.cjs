const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { gsap } = require("gsap");

const lit = { setAttribute(name, value) { this[name] = value; } };
const disc = {
  id: "scene-test-disc",
  dataset: { sceneState: '{"x":100,"y":100,"phase":0}', kind: "phase", radius: "70" },
  firstElementChild: null,
  setAttribute(name, value) { this[name] = value; },
  querySelector() { return lit; },
};
const actions = [
  { target: disc.id, at: 0, duration: 2, to: { phase: 180, x: 200 } },
  { target: disc.id, at: 3, duration: 2, to: { phase: 360, x: 300 } },
];
let scans = 0;
const context = {
  gsap, Intl, window: {},
  document: {
    fonts: { ready: Promise.resolve() },
    querySelectorAll(selector) {
      if (selector === "[data-scene-state]") { scans++; return [disc]; }
      return [];
    },
    getElementById(id) {
      return id === "scene-actions" ? { textContent: JSON.stringify(actions) } : { dataset: { duration: "6" } };
    },
  },
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "..", "katha", "reel_assets", "reel.js"), "utf8"), context);

setImmediate(() => {
  const tl = context.window.__timelines.main;
  const capture = (time) => {
    tl.seek(time, false);
    return JSON.stringify([disc.transform, lit.d]);
  };
  const area = () => {
    const points = lit.d.slice(1, -1).split("L").map(pair => pair.split(",").map(Number));
    return Math.abs(points.reduce((sum, point, i) => {
      const next = points[(i + 1) % points.length];
      return sum + point[0] * next[1] - next[0] * point[1];
    }, 0)) / 2;
  };
  capture(0);
  assert.ok(area() < 1, "new Moon must be dark");
  capture(1);
  const half = area();
  capture(2);
  const full = area();
  assert.ok(Math.abs(half / full - 0.5) < 0.01, "quarter has half the illuminated area");
  assert.ok(Math.abs(full / (Math.PI * 70 ** 2) - 1) < 0.01, "full Moon illuminates the disc");
  capture(5);
  assert.ok(area() < 1, "a complete cycle returns to new Moon");
  const first = capture(1);
  capture(5);
  capture(0);
  assert.equal(capture(1), first, "backward and forward seeks must reproduce the same picture");
  assert.equal(scans, 1, "build scene timeline once, not once per caption element");
  assert.equal(tl.getChildren(false, true, false).filter(tween => tween.targets()[0] === context.window.__sceneStates.get(disc.id).state).length, 2);
  tl.kill();
  gsap.ticker.sleep();
  console.log("Scene phase geometry and deterministic seeking passed.");
});

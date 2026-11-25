// Generic preset engine: every timed element declares data-anim="preset@start[:duration];...".
// All timing is computed in Python from narration word boundaries; this file only maps presets to tweens.
(function () {
  const graphemes = (text) =>
    Array.from(new Intl.Segmenter("ne", { granularity: "grapheme" }).segment(text), (s) => s.segment);
  const later = { immediateRender: false };
  function phasePath(radius, degrees) {
    const angle = ((degrees % 360) + 360) % 360;
    const waxing = angle <= 180;
    const terminator = Math.cos(angle * Math.PI / 180) * (waxing ? 1 : -1);
    const points = [];
    for (let i = 0; i <= 80; i++) {
      const y = -radius + 2 * radius * i / 80;
      points.push([Math.sqrt(Math.max(0, radius * radius - y * y)) * (waxing ? 1 : -1), y]);
    }
    for (let i = 80; i >= 0; i--) {
      const y = -radius + 2 * radius * i / 80;
      points.push([Math.sqrt(Math.max(0, radius * radius - y * y)) * terminator, y]);
    }
    return "M" + points.map(([x, y]) => `${x.toFixed(3)},${y.toFixed(3)}`).join("L") + "Z";
  }

  function buildScenes(tl) {
    document.querySelectorAll(".scene-stage").forEach((el) => {
      const start = Number(el.dataset.sceneStart);
      tl.set(el, { visibility: "visible" }, start);
      tl.set(el, { visibility: "hidden" }, start + Number(el.dataset.sceneDuration));
    });
    const states = new Map();
    document.querySelectorAll("[data-scene-state]").forEach((el) => {
      const state = { x: 0, y: 0, scale: 1, rotation: 0, opacity: 1, angle: 0, phase: 0, draw: 1,
        ...JSON.parse(el.dataset.sceneState) };
      const shape = el.querySelector(":scope > g[clip-path]")?.firstElementChild || el.firstElementChild;
      const update = () => {
        let { x, y } = state;
        if (state.orbit) {
          const a = state.angle * Math.PI / 180;
          x += state.orbit.cx + state.orbit.rx * Math.cos(a);
          y += state.orbit.cy + state.orbit.ry * Math.sin(a);
        }
        el.setAttribute("transform", `translate(${x} ${y}) rotate(${state.rotation}) scale(${state.scale})`);
        el.setAttribute("opacity", state.opacity);
        if (el.dataset.kind === "phase") {
          el.querySelector(".phase-light").setAttribute("d", phasePath(Number(el.dataset.radius), state.phase));
        }
        if (shape && typeof shape.getTotalLength === "function") {
          const length = shape.getTotalLength();
          shape.style.strokeDasharray = `${length}`;
          shape.style.strokeDashoffset = `${length * (1 - state.draw)}`;
        }
      };
      update();
      states.set(el.id, { state, update });
    });
    const plan = JSON.parse(document.getElementById("scene-actions").textContent);
    plan.forEach((action) => {
      const { state, update } = states.get(action.target);
      tl.to(state, { ...action.to, duration: action.duration, ease: "none", onUpdate: update }, action.at);
    });
    window.__sceneStates = states;
  }
  const presets = {
    rise: (tl, el, t) => tl.fromTo(el, { opacity: 0, y: 46, filter: "blur(12px)" },
      { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.5, ease: "power3.out" }, t),
    pop: (tl, el, t) => tl.fromTo(el, { opacity: 0, scale: 0.55 },
      { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.9)" }, t),
    word: (tl, el, t) => tl.fromTo(el, { opacity: 0, y: 20, filter: "blur(9px)" },
      { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.24, ease: "power2.out" }, t),
    drawx: (tl, el, t, d) => tl.fromTo(el, { scaleX: 0 }, { scaleX: 1, duration: d || 0.5, ease: "power2.inOut" }, t),
    drawy: (tl, el, t, d) => tl.fromTo(el, { scaleY: 0 }, { scaleY: 1, duration: d || 0.5, ease: "power2.inOut" }, t),
    tick: (tl, el, t) => tl.fromTo(el, { opacity: 0, scale: 0, rotation: -45 },
      { opacity: 1, scale: 1, rotation: 0, duration: 0.34, ease: "back.out(2.4)" }, t),
    stamp: (tl, el, t) => tl.fromTo(el, { opacity: 0, scale: 2.6, rotation: -20 },
      { opacity: 1, scale: 1, rotation: -7, duration: 0.34, ease: "expo.out" }, t),
    marker: (tl, el, t) => tl.fromTo(el, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, t),
    fill: (tl, el, t, d) => tl.fromTo(el, { scaleX: 0 }, { scaleX: 1, duration: d, ease: "none" }, t),
    float: (tl, el, t, d) => tl.fromTo(el, { y: 0, scale: 1 }, { y: -16, scale: 1.025, duration: d, ease: "sine.inOut", ...later }, t),
    fade: (tl, el, t, d) => tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: d || 0.3 }, t),
    hide: (tl, el, t) => tl.fromTo(el, { opacity: 1 }, { opacity: 0, duration: 0.2, ...later }, t),
    show: (tl, el, t) => tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.25, ...later }, t),
    out: (tl, el, t) => tl.fromTo(el, { opacity: 1, scale: 1, filter: "blur(0px)" },
      { opacity: 0, scale: 0.96, filter: "blur(8px)", duration: 0.2, ease: "power2.in", ...later }, t),
    ink: (tl, el, t) => tl.fromTo(el, { color: el.dataset.from }, { color: el.dataset.to, duration: 0.2, ...later }, t),
    paint: (tl, el, t) => tl.fromTo(el, { backgroundColor: el.dataset.from, color: el.dataset.inkFrom },
      { backgroundColor: el.dataset.to, color: el.dataset.inkTo, duration: 0.25, ...later }, t),
    pulse: (tl, el, t, d) => tl.fromTo(el, { scale: 1 },
      { scale: 1.18, duration: 0.35, yoyo: true, repeat: Math.max(1, Math.floor((d || 1.4) / 0.35) - 1), ease: "sine.inOut", ...later }, t),
    count: (tl, el, t, d) => {
      const state = { v: Number(el.dataset.from || 0) };
      const show = () => { el.textContent = (el.dataset.prefix || "") + Math.round(state.v) + (el.dataset.suffix || ""); };
      show();
      tl.to(state, { v: Number(el.dataset.to), duration: d || 1, ease: "power2.out", onUpdate: show }, t);
    },
    type: (tl, el, t, d) => {
      const parts = graphemes(el.dataset.text);
      const state = { n: 0 };
      el.textContent = "";
      tl.to(state, { n: parts.length, duration: d || parts.length * 0.07, ease: "none",
        onUpdate: () => { el.textContent = parts.slice(0, Math.round(state.n)).join(""); } }, t);
    },
  };

  document.fonts.ready.then(() => {
    const tl = gsap.timeline({ paused: true });
    document.querySelectorAll("[data-anim]").forEach((el) => {
      el.dataset.anim.split(";").filter(Boolean).forEach((spec) => {
        const match = spec.match(/^(\w+)@([\d.]+)(?::([\d.]+))?$/);
        if (!match || !presets[match[1]]) throw new Error("Unknown animation " + spec);
        presets[match[1]](tl, el, Number(match[2]), match[3] ? Number(match[3]) : undefined);
      });
    });
    buildScenes(tl);
    tl.set({}, {}, Number(document.getElementById("main").dataset.duration));
    window.__timelines = window.__timelines || {};
    window.__timelines.main = tl;
  });
})();

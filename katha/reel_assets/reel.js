// Generic preset engine: every timed element declares data-anim="preset@start[:duration];...".
// All timing is computed in Python from narration word boundaries; this file only maps presets to tweens.
(function () {
  const graphemes = (text) =>
    Array.from(new Intl.Segmenter("ne", { granularity: "grapheme" }).segment(text), (s) => s.segment);
  const later = { immediateRender: false };
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
    tl.set({}, {}, Number(document.getElementById("main").dataset.duration));
    window.__timelines = window.__timelines || {};
    window.__timelines.main = tl;
  });
})();

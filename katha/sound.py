"""Original procedural music bed and UI sound effects.

Everything is synthesized from sine waves and seeded noise, so the output carries no third-party
licence. Requires numpy (pip install -r requirements-reel.txt).
"""
import wave

from .studio import StudioError

RATE = 48000
# Semitone offsets from A3 (220 Hz): Am7, Fmaj7, Cmaj7, G6. Two bars each.
PROGRESSION = ([0, 3, 7, 10], [-4, 0, 3, 7], [3, 7, 10, 14], [-2, 2, 5, 7])


def _np():
    try:
        import numpy
    except ImportError as exc:
        raise StudioError("Install reel dependencies: pip install -r requirements-reel.txt") from exc
    return numpy


def _freq(semitones, base=220.0):
    return base * 2 ** (semitones / 12)


def _add(buffer, start, signal, pan=0.0):
    np = _np()
    i = int(start * RATE)
    if i >= buffer.shape[0]:
        return
    signal = signal[: buffer.shape[0] - i]
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buffer[i:i + len(signal), 0] += signal * left * 1.41
    buffer[i:i + len(signal), 1] += signal * right * 1.41


def _tone(freq, length, decay, harmonics=(1.0, 0.35), sweep_to=None):
    np = _np()
    t = np.arange(int(length * RATE)) / RATE
    if sweep_to:
        phase = 2 * np.pi * np.cumsum(np.linspace(freq, sweep_to, len(t))) / RATE
    else:
        phase = 2 * np.pi * freq * t
    wave_ = sum(a * np.sin(phase * (n + 1)) for n, a in enumerate(harmonics))
    attack = np.minimum(1, t / 0.004)
    return wave_ * attack * np.exp(-decay * t)


def _noise(rng, length, decay, highpass=True, band=None):
    np = _np()
    n = rng.standard_normal(int(length * RATE))
    if band:
        spectrum = np.fft.rfft(n)
        f = np.fft.rfftfreq(len(n), 1 / RATE)
        spectrum *= np.exp(-((f - band[0]) / band[1]) ** 2)
        n = np.fft.irfft(spectrum, len(n))
        n /= max(1e-9, np.abs(n).max())
    elif highpass:
        n = np.diff(n, prepend=0) / 2
    t = np.arange(len(n)) / RATE
    return n * np.exp(-decay * t)


def _sum(*signals):
    np = _np()
    out = np.zeros(max(len(s) for s in signals))
    for s in signals:
        out[: len(s)] += s
    return out


def music_bed(duration, bpm=94, seed=7):
    """Return a stereo float array: pad, arpeggio, bass and soft drums, faded in and out."""
    np = _np()
    if not 60 <= bpm <= 140:
        raise StudioError("music.bpm must be between 60 and 140")
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    out = np.zeros((int(duration * RATE) + RATE, 2))
    chord_len = 8 * beat
    for c in range(int(duration / chord_len) + 1):
        chord = PROGRESSION[c % len(PROGRESSION)]
        start = c * chord_len
        t = np.arange(int((chord_len + 0.8) * RATE)) / RATE
        env = np.minimum(1, t / 0.5) * np.clip((chord_len + 0.8 - t) / 0.8, 0, 1)
        for n, semi in enumerate(chord):
            f = _freq(semi)
            for detune, pan in ((0.9985, -0.6), (1.0015, 0.6)):
                pad = np.sin(2 * np.pi * f * detune * t) + 0.22 * np.sin(4 * np.pi * f * detune * t)
                _add(out, start, 0.022 * pad * env, pan)
        for step in range(16):
            note = chord[(0, 1, 2, 3, 2, 1, 2, 3)[step % 8]] + 12
            _add(out, start + step * beat / 2, 0.05 * _tone(_freq(note), 0.9, 5.5), (-0.35, 0.35)[step % 2])
        root = chord[0] - 12 if chord[0] > -3 else chord[0]
        for bar in range(2):
            for offset in (0, 2.5):
                _add(out, start + (bar * 4 + offset) * beat, 0.15 * _tone(_freq(root, 110), 1.0, 3.5, (1.0, 0.0, 0.2)))
    for b in range(int(duration / beat) + 1):
        at = b * beat
        if b % 2 == 0:
            _add(out, at, 0.3 * _tone(110, 0.3, 14, (1.0,), sweep_to=42))
        else:
            _add(out, at, 0.05 * _noise(rng, 0.2, 22))
        _add(out, at + beat / 2, 0.022 * _noise(rng, 0.06, 70), 0.3)
    out = out[: int(duration * RATE)]
    t = np.arange(len(out)) / RATE
    fade = np.minimum(1, t / 0.6) * np.clip((duration - t) / 2.2, 0, 1)
    out *= fade[:, None]
    return out / max(1e-9, np.abs(out).max()) * 0.8


def sfx(kind, rng):
    np = _np()
    if kind == "whoosh":
        n = _noise(rng, 0.38, 0, band=(1800, 1400))
        t = np.arange(len(n)) / RATE
        return 0.22 * n * np.sin(np.pi * np.clip(t / 0.38, 0, 1)) ** 2
    if kind == "pop":
        return 0.32 * _tone(520, 0.12, 32, (1.0, 0.2), sweep_to=1150)
    if kind == "tick":
        return 0.26 * _sum(_tone(2400, 0.04, 140, (1.0,)), _tone(1250, 0.05, 90, (1.0,)))
    if kind == "stamp":
        return _sum(0.45 * _tone(150, 0.2, 18, (1.0, 0.3), sweep_to=55), 0.18 * _noise(rng, 0.12, 40))
    if kind == "chime":
        late = np.concatenate([np.zeros(int(0.09 * RATE)), _tone(1975.5, 1.1, 3.4, (1.0, 0.15))])
        return 0.16 * _sum(_tone(1318.5, 1.2, 3.2, (1.0, 0.15)), late)
    raise StudioError(f"Unknown sound effect: {kind}")


def sfx_track(duration, events, seed=11):
    """events: iterable of (seconds, kind). Returns stereo float array."""
    np = _np()
    rng = np.random.default_rng(seed)
    out = np.zeros((int(duration * RATE), 2))
    for i, (at, kind) in enumerate(sorted(events)):
        if 0 <= at < duration:
            _add(out, at, sfx(kind, rng), (-0.15, 0.15)[i % 2])
    return out


def write_wav(path, samples):
    np = _np()
    data = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(data.tobytes())

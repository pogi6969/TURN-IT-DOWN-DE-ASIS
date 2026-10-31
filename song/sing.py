"""Turn Kokoro TTS words into a sung line: WORLD vocoder re-pitch + time-stretch to the melody,
with singer-style pitch scoops, vibrato, timing, dynamics, breathiness and inhales.

Model files: kokoro-v1.0.onnx and voices-v1.0.bin from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
(set KOKORO_DIR to the folder holding them).
"""
import os
import re

import numpy as np
import pyworld as pw
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly

FS = 24000
FP = 5.0  # WORLD frame period, ms
FPS = 1000 / FP
TL_WORDS = {'ng': 'nang', 'mga': 'manga', 'seen': 'sin', 'okay': 'okey', 'group': 'grup',
            'chat': 'chat', 'haha': 'jaja', 'number': 'namber', 'story': 'stori', 'jacket': 'dyaket',
            'unfollow': 'anfolou', 'follow': 'folou', 'plaza': 'plasa', 'abroad': 'abrod',
            'text': 'tekst', 'call': 'kol'}


def tl_tts(tok):
    w = tok.lower().replace("'", '')
    if w in TL_WORDS:
        return TL_WORDS[w]
    return w.replace('h', 'j')


def wobble(rng, n, win):
    """Unit-variance noise smoothed over `win` frames."""
    win = max(3, win)
    x = rng.normal(0, 1, n + 2 * win)
    k = np.hanning(win)
    y = np.convolve(x, k / k.sum(), 'same')[win:win + n]
    return y / (np.std(y) + 1e-9)


class Singer:
    def __init__(self, lang, syllables, seed=11):
        d = os.environ.get('KOKORO_DIR', '/tmp/claude-0/models')
        self.k = Kokoro(f'{d}/kokoro-v1.0.onnx', f'{d}/voices-v1.0.bin')
        self.lang = lang
        self.syllables = syllables
        self.rng = np.random.default_rng(seed)
        self.cache = {}

    def words(self, line):
        groups = []
        for tok in re.findall(r"[a-zA-Z']+", line.replace('-', ' ')):
            n = len(self.syllables(tok))
            if n == 0 and groups:
                groups[-1][0].append(tok)
                continue
            groups.append([[tok], n])
        return groups

    def tts(self, toks):
        if self.lang == 'en':
            text, voice, lang = ' '.join(toks).replace("'bout", 'about'), 'af_heart', 'en-us'
        else:
            text, voice, lang = ' '.join(tl_tts(t) for t in toks), 'ef_dora', 'es'
        if text not in self.cache:
            s, _ = self.k.create(text, voice=voice, lang=lang, speed=0.8)
            s = np.asarray(s, dtype=np.float64)
            idx = np.nonzero(np.abs(s) > 0.02 * np.max(np.abs(s)))[0]
            s = s[max(0, idx[0] - 200): idx[-1] + 400]
            f0, t = pw.harvest(s, FS, f0_floor=70, f0_ceil=800, frame_period=FP)
            sp = pw.cheaptrick(s, f0, t, FS)
            ap = pw.d4c(s, f0, t, FS)
            self.cache[text] = (f0, sp, ap)
        return self.cache[text]

    @staticmethod
    def split(f0, sp, n):
        """Syllable segments [(a, peak, voiced_end, b)] from energy peaks of voiced frames."""
        T = len(f0)
        e = np.log(np.sum(sp, 1) + 1e-12) * (f0 > 0)
        e = np.convolve(e, np.ones(5) / 5, 'same')
        peaks = []
        for i in np.argsort(-e):
            if e[i] <= 0:
                break
            if all(abs(i - p) >= 10 for p in peaks):
                peaks.append(int(i))
            if len(peaks) == n:
                break
        if len(peaks) < n:
            peaks = [int(T * (j + 0.5) / n) for j in range(n)]
        peaks.sort()
        bounds = [0] + [int(peaks[j] + np.argmin(e[peaks[j]:peaks[j + 1]])) for j in range(n - 1)] + [T]
        segs = []
        for j in range(n):
            a, b = bounds[j], bounds[j + 1]
            p = max(a, min(peaks[j] - 2, a + 16))
            v = np.nonzero(f0[a:b] > 0)[0]
            ve = a + v[-1] + 1 if len(v) else b
            ve = max(ve, p + 2)
            segs.append((a, p, min(ve, b), b))
        return segs

    def inhale(self, dur):
        n = int(dur * FS)
        X = np.fft.rfft(self.rng.normal(0, 1, n))
        f = np.fft.rfftfreq(n, 1 / FS)
        shape = 0.6 * np.exp(-((f - 1600) / 900) ** 2) + np.exp(-((f - 4200) / 1800) ** 2) + 0.15
        shape[f < 300] = 0
        y = np.fft.irfft(X * shape, n)
        e = np.sin(np.pi / 2 * np.linspace(0, 1, n)) ** 2
        k = int(0.015 * FS)
        e[-k:] *= np.linspace(1, 0, k)
        y *= e
        return y / (np.sqrt(np.mean(y ** 2)) + 1e-9)

    def line(self, text, notes, out_sr=44100, breath=True):
        """notes: [(time, dur, midi, vowel)] one per syllable. Returns (audio, start_time)."""
        rng = self.rng
        syl = []
        for toks, n in self.words(text):
            f0, sp, ap = self.tts(toks)
            wj = float(np.clip(rng.normal(0.012, 0.012), -0.02, 0.04))  # a hair behind the beat
            for j, seg in enumerate(self.split(f0, sp, n)):
                syl.append((f0, sp, ap, seg, j == n - 1, wj))
        nn = min(len(syl), len(notes))
        ons = [syl[i][3][1] - syl[i][3][0] for i in range(nn)]
        t_ref = notes[0][0] + syl[0][5] - ons[0] / FPS - 0.02
        nuc = [int(round((notes[i][0] + syl[i][5] - t_ref) * FPS)) for i in range(nn)]
        F0, SP, AP, GN, BR = [], [], [], [], []
        cur, prev_m = 0, None
        for i in range(nn):
            f0, sp, ap, (a, p, ve, b), wend, _ = syl[i]
            t, d, m, _ = notes[i]
            on = p - a
            start = nuc[i] - on
            if start < cur and on > 1:  # running late: shorten the consonant onset
                cut = min(on - 1, cur - start)
                a, on, start = a + cut, on - cut, start + cut
            gap = start - cur
            if gap > 0:
                F0.append(np.zeros(gap))
                SP.append(np.repeat(sp[a:a + 1], gap, 0))
                AP.append(np.ones((gap, ap.shape[1])))
                GN.append(np.full(gap, 1e-3))
                BR.append(np.zeros(gap))
                cur += gap
            legato = i > 0 and gap <= 0
            coda = (b - ve) if wend else 0
            note_end = nuc[i] + int(d * FPS)
            end = note_end if i + 1 == nn else min(note_end, nuc[i + 1] - ons[i + 1])
            if i + 1 == nn:
                end -= 4
            rest_after = i + 1 == nn or note_end < nuc[i + 1] - ons[i + 1] - 10
            body = max(3, end - (cur + on) - coda)
            pos = np.concatenate([np.arange(a, p, dtype=float), np.linspace(p, max(p, ve - 1), body),
                                  np.arange(ve, ve + coda, dtype=float)])
            i0 = np.clip(np.floor(pos).astype(int), 0, len(f0) - 1)
            i1 = np.clip(i0 + 1, 0, len(f0) - 1)
            w = (pos - np.floor(pos))[:, None]
            L = len(pos)
            voiced = f0[i0] > 0
            voiced[on:on + body] = True
            tt = (np.arange(L) - on) / FPS  # seconds from the vowel
            dur_s = body / FPS
            # pitch: scoop into the note, vibrato that blooms late, drift, jitter, fall at phrase ends
            if legato and abs(prev_m - m) <= 9:
                st, tau = prev_m - m, rng.uniform(0.035, 0.06)
            else:
                st, tau = -rng.uniform(0.4, 1.0), rng.uniform(0.05, 0.08)
            semis = m + st * np.exp(-np.maximum(tt, 0) / tau)
            if legato and m - prev_m >= 3:
                semis += 0.25 * np.exp(-((tt - 0.09) / 0.04) ** 2)
            od, dv, vr = rng.uniform(0.2, 0.35), rng.uniform(0.15, 0.32), rng.uniform(5.0, 5.9)
            vph = 2 * np.pi * np.cumsum(vr + 0.35 * wobble(rng, L, 60)) / FPS + rng.random() * 6.3
            semis += np.clip((tt - od) / 0.35, 0, 1) * dv * np.sin(vph)
            semis += 0.07 * wobble(rng, L, 40) + 0.025 * wobble(rng, L, 3)
            fo = np.clip((tt - (dur_s - 0.15)) / 0.15, 0, 1) if rest_after else np.zeros(L)
            semis -= fo ** 2 * rng.uniform(0.4, 1.3)
            # loudness: phrase arc, soft attack, swell on long notes, shimmer, release
            g = np.full(L, 0.86 + 0.14 * np.sin(np.pi * (i + 0.5) / nn))
            g *= np.clip(0.85 + 0.15 * tt / 0.04, 0.85, 1) if legato else np.clip(0.6 + 0.4 * tt / 0.06, 0.6, 1)
            if dur_s > 0.5:
                g *= 1 + 0.12 * np.sin(np.pi * np.clip(tt / dur_s, 0, 1))
            g *= (1 + 0.05 * wobble(rng, L, 8)) * (1 - 0.85 * fo)
            br = 0.03 + 0.3 * fo
            if not legato:
                br = br + 0.12 * np.clip(1 - (tt + 0.02) / 0.06, 0, 1)
            F0.append(np.where(voiced, 440 * 2 ** ((semis - 69) / 12), 0.0))
            SP.append(sp[i0] * (1 - w) + sp[i1] * w)
            AP.append(ap[i0] * (1 - w) + ap[i1] * w)
            GN.append(g)
            BR.append(br)
            cur += L
            prev_m = m
        GN, BR = np.concatenate(GN), np.concatenate(BR)
        SP = np.concatenate(SP) * (GN ** 2)[:, None]
        AP = np.concatenate(AP)
        AP = 1 - (1 - AP) * (1 - np.clip(BR, 0, 0.9)[:, None] * np.linspace(0.25, 1, AP.shape[1])[None, :])
        y = pw.synthesize(np.ascontiguousarray(np.concatenate(F0)), np.ascontiguousarray(SP),
                          np.ascontiguousarray(AP), FS, FP)
        loud = y[np.abs(y) > 0.05 * np.max(np.abs(y))]
        y = y / (np.sqrt(np.mean(loud ** 2)) + 1e-9) * 0.12
        t0 = t_ref
        if breath and rng.random() < 0.75:
            bd = rng.uniform(0.18, 0.3)
            y = np.concatenate([self.inhale(bd) * 0.12 * rng.uniform(0.06, 0.12), np.zeros(int(0.03 * FS)), y])
            t0 -= bd + 0.03
        if out_sr == 44100:
            y = resample_poly(y, 147, 80)
        return y, t0

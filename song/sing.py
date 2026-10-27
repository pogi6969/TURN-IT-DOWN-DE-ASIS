"""Turn Kokoro TTS words into a sung line: WORLD vocoder re-pitch + time-stretch to the melody.

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
TL_WORDS = {'ng': 'nang', 'mga': 'manga', 'seen': 'sin', 'okay': 'okey', 'group': 'grup',
            'chat': 'chat', 'haha': 'jaja'}


def tl_tts(tok):
    w = tok.lower().replace("'", '')
    if w in TL_WORDS:
        return TL_WORDS[w]
    return w.replace('h', 'j')


class Singer:
    def __init__(self, lang, syllables):
        d = os.environ.get('KOKORO_DIR', '/tmp/claude-0/models')
        self.k = Kokoro(f'{d}/kokoro-v1.0.onnx', f'{d}/voices-v1.0.bin')
        self.lang = lang
        self.syllables = syllables
        self.rng = np.random.default_rng(11)
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
            s, sr = self.k.create(text, voice=voice, lang=lang, speed=0.95)
            s = np.asarray(s, dtype=np.float64)
            idx = np.nonzero(np.abs(s) > 0.02 * np.max(np.abs(s)))[0]
            s = s[max(0, idx[0] - 200): idx[-1] + 400]
            f0, sp, ap = pw.wav2world(s, FS, frame_period=FP)
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

    def line(self, text, notes, out_sr=44100):
        """notes: [(time, dur, midi, vowel)] one per syllable. Returns (audio, start_time)."""
        frames_f0, frames_sp, frames_ap = [], [], []
        t_cursor = None
        lead = 0.0
        ni = 0
        prev_m = None
        start = notes[0][0]
        for toks, n in self.words(text):
            f0, sp, ap = self.tts(toks)
            segs = self.split(f0, sp, n)
            for j, (a, p, ve, b) in enumerate(segs):
                if ni >= len(notes):
                    break
                t, d, m, _ = notes[ni]
                onset = p - a
                coda = (b - ve) if j == n - 1 else 0
                if ni == 0:
                    lead = onset * FP / 1000
                    t_cursor = start - lead
                # frames until this syllable's nucleus should hit the note time
                gap = int(round((t - onset * FP / 1000 - t_cursor) * 1000 / FP))
                if gap > 0:
                    frames_f0.append(np.zeros(gap))
                    frames_sp.append(np.repeat(frames_sp[-1][-1:] if frames_sp else sp[:1], gap, 0) * 1e-4)
                    frames_ap.append(np.ones((gap, ap.shape[1])))
                    t_cursor += gap * FP / 1000
                D = max(4, int(d * 1000 / FP) - (6 if j == n - 1 else 0))
                body = max(2, D - coda)
                idx = np.concatenate([np.arange(a, p),
                                      np.linspace(p, ve - 1, body),
                                      np.arange(ve, ve + coda)])
                ii = np.clip(np.round(idx).astype(int), 0, len(f0) - 1)
                voiced = f0[ii] > 0
                voiced[len(np.arange(a, p)):len(np.arange(a, p)) + body] |= idx[(p - a):(p - a) + body] < ve - 1
                L = len(ii)
                tt = np.arange(L) * FP / 1000
                semis = np.full(L, float(m))
                st = prev_m if prev_m is not None and abs(prev_m - m) <= 7 else m - 0.6
                semis += (st - m) * np.exp(-tt / 0.045)
                semis += np.clip((tt - 0.28) / 0.35, 0, 1) * 0.22 * np.sin(2 * np.pi * 5.3 * tt + self.rng.random() * 6)
                semis += 0.06 * np.sin(2 * np.pi * 0.9 * tt + self.rng.random() * 6)
                if d > 0.6:  # slight fall-off at the end of long notes
                    semis -= np.clip((tt - (L * FP / 1000 - 0.12)) / 0.12, 0, 1) * 0.5
                nf0 = np.where(voiced, 440 * 2 ** ((semis - 69) / 12), 0.0)
                frames_f0.append(nf0)
                frames_sp.append(sp[ii])
                frames_ap.append(ap[ii])
                t_cursor += L * FP / 1000
                prev_m = m
                ni += 1
        f0 = np.concatenate(frames_f0)
        sp = np.ascontiguousarray(np.concatenate(frames_sp))
        ap = np.ascontiguousarray(np.concatenate(frames_ap))
        y = pw.synthesize(f0, sp, ap, FS, FP)
        y = resample_poly(y, 147, 80) if out_sr == 44100 else y
        y /= np.sqrt(np.mean(y ** 2)) + 1e-9
        return y * 0.12, start - lead

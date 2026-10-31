"""Render "Kunwari Okay": demo mix, karaoke mix and lyric video.

Usage: python3 make_song.py [tl|en] [out_dir]
Needs numpy, pillow and ffmpeg.
"""
import os
import re
import subprocess
import sys
import wave
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SR = 44100
BPM = 80
BEAT = 60 / BPM
BAR = 4 * BEAT
S16 = BEAT / 4
LANG = sys.argv[1] if len(sys.argv) > 1 else 'tl'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- song data

CHORDS = {
    'D': (2, (0, 4, 7)), 'E': (4, (0, 4, 7)), 'A': (9, (0, 4, 7)), 'B': (11, (0, 4, 7)),
    'G': (7, (0, 4, 7)), 'C': (0, (0, 4, 7)), 'Cadd9': (0, (0, 4, 7, 2)), 'Bm': (11, (0, 3, 7)), 'Em': (4, (0, 3, 7)), 'F#m': (6, (0, 3, 7)),
}
D_SCALE = [2, 4, 6, 7, 9, 11, 1]

VERSE = ['D', 'A', 'Bm', 'G'] * 2
PRE = ['Em', 'F#m', 'G', 'A']
CHORUS = ['G', 'A', 'F#m', 'Bm', 'G', 'A', 'D', 'A'] * 2

V1 = ["Alas-sais, gising na naman", "Ngiti sa salamin, pilit lang",
      "Sa group chat, puro \"haha\" ako", "Pero tahimik ang kwarto ko",
      "\"Ang tatag mo,\" sabi nila", "'Di nila alam, gabi-gabi'y giyera",
      "Sa unan ko binubuhos ang luha", "Para walang mag-alala"]
PRE_L = ["At kung tanungin mo kung kumusta na ako",
         "Sanay na 'kong sumagot ng \"ayos lang 'to\""]
CH = ["Kunwari okay, kunwari buo", "Kunwari 'di nadudurog ang puso",
      "Tinatawanan ko na lang ang sakit", "Baka 'pag umiyak, 'di na 'ko tumigil",
      "Kunwari okay, kahit hindi na", "Sana may makapansin, kahit isa",
      "Na sa likod ng \"okay lang ako\"", "May batang naghihintay ng yakap mo"]
V2 = ["Panganay, ako raw ang sandalan", "Pero sa'n ako sasandal, saan?",
      "Si Mama, pagod sa trabaho", "Si Papa, matagal nang 'di umuwi rito",
      "Ikaw sana ang pahinga ko", "Pero \"seen\" lang ang sagot mo",
      "Gaya ng lahat, umalis ka rin", "Naiwan akong buo kunwari pa rin"]
BR = ["Hindi ako mahina, pagod lang", "Hindi ako sumusuko, nagpapahinga lang",
      "At kung bukas, gigising pa rin ako", "Ibig sabihin, kaya ko pa 'to"]
FC = ["Ayoko nang magkunwari pa", "Hindi ako okay, at okay lang 'yon pala",
      "Iiyak ko na lahat ng sakit", "Bukas, sisikat din ulit ang langit",
      "Kaya ikaw, na nakangiti rin", "Na tulad ko, pagod din",
      "Hindi ka nag-iisa rito", "Yayakapin kita, totoo"]

EN = dict(
    V1=["Six a.m., wake up again", "Practice my smile in the mirror, pretend",
        "Typing \"lol\" in the group chat", "But nobody's laughing where I'm at",
        "\"You're so strong,\" that's what they say", "They don't see the war I fight every day",
        "I cry it all into my pillow", "So nobody has to know"],
    PRE_L=["And if you ask me how I'm doing tonight", "I'm so used to saying \"yeah, I'm alright\""],
    CH=["I'm fine, I'm fine, I'm holding on", "Pretending that my heart's not already gone",
        "I laugh it off, I hide the pain", "'Cause if I start crying, I won't stop again",
        "I'm fine, I'm fine, even when I'm not", "Wish somebody noticed what I've got",
        "Behind every \"don't worry 'bout me\"", "There's a kid still waiting for somebody"],
    V2=["Oldest child, I'm the one they lean on", "But where do I go when my strength is gone?",
        "Mom's too tired from working late", "Dad's been gone, I stopped asking why he never came",
        "You were supposed to be my rest", "But you left me on \"seen\" like all the rest",
        "Like everyone, you walked away", "And I'm still pretending I'm okay"],
    BR=["I'm not weak, I'm just tired", "I'm not giving up, I'm just catching my breath",
        "And if tomorrow I still wake up", "It means I'm still strong enough"],
    FC=["I don't wanna pretend no more", "I'm not okay, and that's what tears are for",
        "I'll cry out every bit of the pain", "Tomorrow the sun will rise again",
        "So you, who's smiling through it too", "Tired like me, I see you",
        "You're not alone in this", "I'll hold you through it, I promise"],
    OUTRO=["How are you?", "...Really, though?"])
INTRO_CH, BRIDGE_CH, OUTRO_CH = ['D', 'A', 'Bm', 'G'], ['Bm', 'A', 'G', 'D', 'Bm', 'A', 'G', 'B'], ['G', 'A', 'D', 'D']
TITLE, HOOK, SLUG, END_MSG = 'Kunwari Okay', 'Kunwari okay', 'kunwari-okay', 'Kumusta ka, totoo?  Kamustahin mo rin sila.'
OUTRO = ["Kumusta ka?", "...'Yung totoo?"]
if LANG == 'en':
    V1, PRE_L, CH, V2, BR, FC, OUTRO = (EN[k] for k in ('V1', 'PRE_L', 'CH', 'V2', 'BR', 'FC', 'OUTRO'))
    TITLE, HOOK, SLUG, END_MSG = "I'm Fine", "I'm fine, I'm fine", 'im-fine', 'How are you, really?  Check on your people.'
if LANG == 'bcl':
    V1 = ["Makusog an uran sa atop", "Si Nanay nagdadasal sa may kandila",
          "Mayo nin kuryente, mayo nin signal", "Ako sana asin an sakong luha",
          "Sabi ninda, sanay na kita sa bagyo", "Taga-Bikol, dai nagtatangis",
          "Pero an bagyo sa laog kan puso ko", "Mayo nin nakakaaram"]
    PRE_L = ["Kaya kun maghapot ka kun kumusta na ako",
             "Sasabihon ko man giraray, \"Marhay man ako\""]
    CH = ["Matapos an bagyo, masirang giraray an aldaw", "Maski ngunyan, garo dai ko na kaya",
          "Itatangis ko sana an gabos na kulog", "Dangan matindog giraray ako",
          "Matapos an bagyo, dai na ako matatakot", "Ta an uran, dai man pirmi",
          "Kun ika man nasa bagyo ngunyan", "Kapot sako, dai taka babayaan"]
    V2 = ["Si Tatay yaon sa abroad", "Nakikita ko sana sa video call",
          "Ika na nagsabing dai ka mahali", "Ika man palan an enot na nagbaya",
          "Nabasa kan uran an satong litrato", "Garo kita, nawara na sana",
          "Dakul na bagyo an nag-abot sa sakong buhay", "Alagad nakatindog pa man giraray"]
    BR = ["Bako ako maluya, pagal sana", "Bako ako nagsusuko, nagpapahingalo sana",
          "Kun sa aga, magmamata pa ako", "Boot sabihon, kaya ko pa ini"]
    FC = ["Matapos an bagyo, dai na ako magtatago", "Bako ako marhay, asin marhay man iyan",
          "Itatangis ko an gabos na kulog", "Sa aga, maliwanag giraray an langit",
          "Kaya ika, na nakangirit man", "Maski pagal, maski makulog",
          "Dai ka nagsosolo digdi", "Kukugoson taka, totoo"]
    OUTRO = ["Kumusta ka?", "...An totoo?"]
    TITLE, HOOK, SLUG, END_MSG = 'Matapos an Bagyo', 'Matapos an bagyo, masirang', 'matapos-an-bagyo', 'Kumusta ka, an totoo?  Hapota man sinda.'
if LANG == 'bcl5':
    D_SCALE = [7, 9, 11, 0, 2, 4, 6]
    VERSE = ['G', 'Cadd9', 'Em', 'D'] * 2
    PRE = ['Em', 'C', 'D', 'D']
    CHORUS = ['G', 'Cadd9', 'Em', 'D'] * 4
    INTRO_CH, BRIDGE_CH, OUTRO_CH = ['G', 'Cadd9', 'Em', 'D'], ['Em', 'C', 'G', 'D', 'Em', 'C', 'D', 'E'], ['C', 'D', 'G', 'G']
    V1 = ["Nakita ko sa story mo", "Kaiba mo na an iba", "Nakangirit ka na giraray",
          "Ako digdi, nagdudumdom pa", "Nagdiklom an langit sa luwas", "Nag-uuran sa sakong kwarto",
          "Signal number singko sa laog ko", "Dai ko na aram an gigibohon"]
    PRE_L = ["Kun mahiling ko kamong duwa", "Itaas na an signal, ta madatong na ako"]
    CH = ["Ako an signal number singko", "Kun maglakaw kamo sa plaza, maguuran",
          "Saindong payong, lulupad sa doros", "Basang-basa kamo pag-uli",
          "Ako an signal number singko", "Dai kamo makakaiwas sa sakong uran",
          "Alagad pag nag-abot an aldaw", "May balangaw man na maabot"]
    V2 = ["Nag-unfollow, nag-follow giraray", "Yaon pa sako an jacket mo",
          "Si Nanay mo, nagte-text pa sako", "Nuarin daw ako mabisita?",
          "Dinilit ko na an satong chat", "Pero dumdom ko pa an gabos",
          "Bako ako dating arog kaini", "Ika an nagtukdo sako magdalugdog"]
    BR = ["Pero gabos na bagyo, natatapos man", "Sa aga, ako naman an masirang",
          "Kaya ngunyan, bayae mo na ako", "Mag-uuran muna ako"]
    FC = ["Ako an signal number singko", "Alagad pagal na ako magdalugdog",
          "Dai ko na kamo babagyohon", "Sakong sadiri an papayongan ko",
          "Ako an signal number singko", "Sa huri, ako man an makakahiling nin aldaw",
          "Paaram, padaba ko", "Dai na taka babasaon"]
    OUTRO = ["Signal number singko...", "...pero matatapos man ini"]
    TITLE, HOOK, SLUG, END_MSG = 'Signal No. 5', 'Ako an signal number singko', 'signal-no-5', 'Gabos na bagyo, natatapos man.'

# (label, chords per bar, lyric lines, bars per line, energy, transpose, register lo/hi)
SECTIONS = [
    ('Intro', INTRO_CH, [], 1, 0, 0, None),
    ('Verse 1', VERSE, V1, 1, 1, 0, (62, 71)),
    ('Pre-Chorus', PRE, PRE_L, 2, 2, 0, (64, 73)),
    ('Chorus', CHORUS, CH, 2, 3, 0, (66, 76)),
    ('Verse 2', VERSE, V2, 1, 2, 0, (62, 71)),
    ('Pre-Chorus', PRE, PRE_L, 2, 2, 0, (64, 73)),
    ('Chorus', CHORUS, CH, 2, 3, 0, (66, 76)),
    ('Bridge', BRIDGE_CH, BR, 2, 2, 0, (64, 76)),
    ('Final Chorus', CHORUS, FC, 2, 4, 2, (66, 76)),
    ('Outro', OUTRO_CH, OUTRO, 2, 0, 2, (64, 71)),
]

# ---------------------------------------------------------------- helpers

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def syllables(line):
    """Tagalog-ish syllables: one per vowel, a few English digraphs merged."""
    out = []
    if LANG == 'en':
        for word in re.findall(r"[a-zA-Z']+", line.replace('-', ' ')):
            w = word.lower().replace("'", '')
            w = re.sub(r'([^aeiouy])e$', r'\1', w) if len(w) > 2 else w
            groups = re.findall(r'[aeiouy]+', w) or ['a']
            for i, g in enumerate(groups):
                v = 'a' if g[0] == 'y' else g[0]
                out.append((v, i == len(groups) - 1))
        return out
    for word in re.findall(r"[a-zA-Z']+", line.replace('-', ' ')):
        w = word.lower().replace("'", '')
        w = w.replace('ee', 'i').replace('ou', 'u').replace('oo', 'u')
        vowels = [c for c in w if c in 'aeiou']
        for i, v in enumerate(vowels):
            out.append((v, i == len(vowels) - 1))  # (vowel, word end)
    return out


def chord_tones(name, tr=0):
    root, iv = CHORDS[name]
    return [(root + i + tr) % 12 for i in iv]


def nearest(pcs, target, lo, hi):
    cands = [m for m in range(lo - 2, hi + 3) if m % 12 in pcs]
    return min(cands, key=lambda m: (abs(m - target), m))


def scale_step(m, steps, scale):
    pcs = sorted(scale)
    idx = [x for x in range(m - 14, m + 15) if x % 12 in pcs]
    i = min(range(len(idx)), key=lambda j: abs(idx[j] - m))
    return idx[max(0, min(len(idx) - 1, i + steps))]


def make_melody(line, nbars, chords, lo, hi, seed_key, start_hi):
    """Return list of (offset16, dur16, midi, vowel) in key of D."""
    syl = syllables(line)
    n = len(syl)
    total = nbars * 16
    rng = np.random.default_rng(zlib.crc32(seed_key.encode()))
    pick = 2 if nbars > 1 else 0
    avail = total - pick - (4 if nbars > 1 else 2)
    durs = [2] * (n - 1)
    i = 0
    while sum(durs) + 3 > avail and i < len(durs):
        durs[i] = 1
        i += 2 if i + 2 < len(durs) else 1
    # stretch word endings / commas in roomy lines
    ends = [k for k in range(n - 1) if syl[k][1]]
    k = 0
    while avail - sum(durs) > 10 and ends:
        durs[ends[k % len(ends)]] += 2
        k += 1
    durs.append(max(2, avail - sum(durs)))
    notes = []
    t = pick
    cur = nearest(chord_tones(chords[0]), start_hi, lo, hi)
    for j, (v, _) in enumerate(syl):
        bar = min(nbars - 1, t // 16)
        ch = chord_tones(chords[bar])
        frac = j / max(1, n - 1)
        bias = 1 if frac < 0.45 else -1
        step = rng.choice([-2, -1, -1, 0, 1, 1, 2]) + (bias if rng.random() < 0.45 else 0)
        nxt = scale_step(cur, int(step), D_SCALE)
        if t % 4 == 0 or j == n - 1:
            nxt = nearest(ch, nxt, lo, hi)
        nxt = max(lo, min(hi, nxt))
        if j == 0:
            nxt = cur
        notes.append((t, durs[j], nxt, v))
        cur = nxt
        t += durs[j]
    return notes


# ---------------------------------------------------------------- timeline

events = []      # (time, kind, data)
lyric_track = []  # (start, end, text, section, notes_abs)
chord_track = []  # (start, chord, transpose, energy)
bar = 0
melody_cache = {}
for label, chords, lines, bpl, energy, tr, reg in SECTIONS:
    sec_start = bar * BAR
    for i, c in enumerate(chords):
        chord_track.append(((bar + i) * BAR, c, tr, energy, label, i == 0))
    for li, line in enumerate(lines):
        lb = bar + li * bpl
        cs = chords[li * bpl:(li + 1) * bpl]
        lo, hi = reg
        key = line
        if line.startswith(HOOK):
            key = 'hook'
        if key not in melody_cache:
            start_hi = (lo + hi) // 2 + (2 if energy >= 3 else -1)
            melody_cache[key] = make_melody(line, bpl, cs, lo, hi, key, start_hi)
        notes = [(lb * BAR + o * S16, d * S16, m + tr, v) for o, d, m, v in melody_cache[key]]
        lyric_track.append((lb * BAR, (lb + bpl) * BAR, line, label, notes))
    bar += len(chords)
SONG_LEN = bar * BAR + 5.0
N = int(SONG_LEN * SR)
print(f'song length {SONG_LEN:.1f}s, {bar} bars')

# ---------------------------------------------------------------- synths

rng = np.random.default_rng(7)


def env_adsr(n, a, r, sustain_decay=0.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t * sustain_decay)
    rn = min(n, int(r * SR))
    if rn > 0:
        e[-rn:] *= np.linspace(1, 0, rn)
    return e


_piano = {}


def piano(m, dur, vel):
    key = (m, round(dur, 2))
    if key not in _piano:
        n = int((dur + 0.6) * SR)
        t = np.arange(n) / SR
        f = mtof(m)
        s = np.zeros(n)
        for k in range(1, 10):
            fk = f * k * (1 + 0.0004 * k * k)
            if fk > 9000:
                break
            s += np.sin(2 * np.pi * fk * t) * (1 / k ** 1.4) * np.exp(-t * (0.9 + 0.55 * k))
        s += 0.4 * np.sin(2 * np.pi * f * 1.002 * t) * np.exp(-t * 1.1)
        e = np.minimum(1, t / 0.004)
        off = int(dur * SR)
        e[off:] *= np.exp(-(t[off:] - dur) * 9)
        _piano[key] = s * e
    return _piano[key] * vel


def pad(chord_midis, dur, tr_seed):
    n = int((dur + 0.8) * SR)
    t = np.arange(n) / SR
    L = np.zeros(n)
    R = np.zeros(n)
    for m in chord_midis:
        f = mtof(m)
        for det, ch in ((-0.11, L), (0.13, R)):
            fd = f * 2 ** (det / 12)
            ph = rng.random() * 6.28
            for k in range(1, 9):
                ch += np.sin(2 * np.pi * fd * k * t + ph * k) / k ** 1.7
    e = np.minimum(1, t / 0.6)
    off = int(dur * SR)
    e[off:] *= np.exp(-(t[off:] - dur) * 4)
    return L * e, R * e


def bass(m, dur):
    n = int((dur + 0.1) * SR)
    t = np.arange(n) / SR
    f = mtof(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return s * env_adsr(n, 0.008, 0.12, 1.2)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    s[:200] += rng.normal(0, 0.3, 200) * np.linspace(1, 0, 200)
    return s


def snare():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    noise = noise - np.concatenate([[0], noise[:-1]]) * 0.6
    return 0.55 * noise * np.exp(-t * 16) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28)


def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    x = rng.normal(0, 1, n)
    x = np.diff(np.diff(x, prepend=0), prepend=0)
    return x * np.exp(-t * (14 if open_ else 70)) * 0.25


def crash():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    x = np.diff(rng.normal(0, 1, n), prepend=0)
    return x * np.exp(-t * 1.8) * 0.35


def swell(dur):
    n = int(dur * SR)
    x = np.diff(rng.normal(0, 1, n), prepend=0)
    return x * np.linspace(0, 1, n) ** 3 * 0.25


FORMANTS = {
    'a': ((800, 80, 1.0), (1150, 90, 0.5), (2900, 120, 0.10)),
    'e': ((400, 70, 1.0), (1900, 100, 0.35), (2650, 120, 0.12)),
    'i': ((300, 60, 1.0), (2200, 100, 0.25), (3000, 120, 0.10)),
    'o': ((450, 70, 1.0), (800, 80, 0.45), (2830, 120, 0.06)),
    'u': ((330, 60, 1.0), (700, 80, 0.3), (2700, 120, 0.04)),
}


def voice(m, dur, vowel, prev_m, vel):
    """Additive vowel singer: harmonics shaped by vowel formants, glide + vibrato."""
    n = int((dur + 0.12) * SR)
    t = np.arange(n) / SR
    glide = 0.0 if prev_m is None else (prev_m - m) * np.exp(-t / 0.035)
    vib_amt = np.clip((t - 0.22) / 0.3, 0, 1) * 0.28
    vib = vib_amt * np.sin(2 * np.pi * 5.4 * t + rng.random() * 6)
    drift = 0.05 * np.sin(2 * np.pi * 0.7 * t + rng.random() * 6)
    f0 = mtof(m) * 2 ** ((glide + vib + drift) / 12)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    fb = mtof(m)
    s = np.zeros(n)
    for k in range(1, 40):
        fk = fb * k
        if fk > 5500:
            break
        a = 0.015
        for F, B, g in FORMANTS[vowel]:
            a += g / np.sqrt(1 + ((fk - F) / B) ** 2)
        s += a / k ** 0.6 * np.sin(k * ph)
    breath = rng.normal(0, 1, n)
    breath = np.diff(breath, prepend=0) * 0.012
    e = env_adsr(n, 0.045, 0.11, 0.15)
    swell_ = 0.8 + 0.2 * np.minimum(1, t / max(0.3, dur))
    return (s + breath) * e * swell_ * vel


def add(buf, x, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[:j - i] * gain


def reverb(x, seconds=2.2, seed=1):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = r.normal(0, 1, n) * np.exp(-t / 0.5)
    ir[: int(0.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x)]
    return y


# ---------------------------------------------------------------- render

pianoL = np.zeros(N); pianoR = np.zeros(N)
padL = np.zeros(N); padR = np.zeros(N)
bassB = np.zeros(N)
drums = np.zeros(N); drumsR = np.zeros(N)
vox = np.zeros(N)
vox2 = np.zeros(N)
vox3 = np.zeros(N)

K, SN = kick(), snare()
for idx, (t0, c, tr, energy, label, first) in enumerate(chord_track):
    pcs = chord_tones(c, tr)
    root = (CHORDS[c][0] + tr) % 12
    rh = sorted(nearest([p], 64, 58, 72) for p in pcs)
    lh = 38 + (root - 2) % 12
    if energy <= 1:
        pat = [rh[0], rh[1], rh[2], rh[1] + 12 if rh[1] + 12 < 80 else rh[2], rh[2], rh[1], rh[0] + 12, rh[1]]
        add(pianoL, piano(lh, BAR * 0.95, 0.5), t0)
        for k, m in enumerate(pat):
            add(pianoR if k % 2 else pianoL, piano(m, BEAT * 1.4, 0.32 if k % 2 else 0.38), t0 + k * BEAT / 2)
    else:
        v = 0.30 if energy == 2 else 0.36
        for beat_pos, dur in ((0, 1.5), (1.5, 1), (2.5, 1.5)):
            for m in rh:
                add(pianoL, piano(m, BEAT * dur, v), t0 + beat_pos * BEAT)
                add(pianoR, piano(m + 12, BEAT * dur, v * 0.45), t0 + beat_pos * BEAT)
        add(pianoL, piano(lh, BAR, 0.45), t0)
    if energy >= 2:
        pl, pr = pad([m + 12 for m in rh] + [rh[0]], BAR, idx)
        g = {2: 0.05, 3: 0.08, 4: 0.1}[energy]
        add(padL, pl, t0, g); add(padR, pr, t0, g)
    if energy >= 2 and label not in ('Pre-Chorus',) or (label == 'Pre-Chorus'):
        if energy >= 2:
            broot = 33 + (root - 9) % 12
            add(bassB, bass(broot, BEAT * 2), t0, 0.5)
            add(bassB, bass(broot, BEAT * 1.5), t0 + BEAT * 2.5, 0.42)
    if energy >= 3:
        lvl = 1.0 if energy == 4 else 0.85
        add(drums, K, t0, 0.9 * lvl); add(drums, K, t0 + 2.5 * BEAT, 0.7 * lvl)
        add(drums, SN, t0 + BEAT, 0.6 * lvl); add(drums, SN, t0 + 3 * BEAT, 0.6 * lvl)
        for k in range(8):
            add(drumsR, hat(k == 7), t0 + k * BEAT / 2, 0.9 if k % 2 == 0 else 0.6)
        if first:
            add(drums, crash(), t0, 0.8)
    elif energy == 2 and label != 'Bridge':
        add(drums, K, t0, 0.5)
        add(drums, SN * 0.5, t0 + 3 * BEAT, 0.45)
        for k in range(4):
            add(drumsR, hat(), t0 + k * BEAT, 0.5)
    elif label == 'Bridge':
        add(drums, K, t0, 0.55)
        if idx % 2:
            add(drums, SN, t0 + 3 * BEAT, 0.3)
    if label == 'Pre-Chorus' and chord_track[idx + 1][4].endswith('Chorus') if idx + 1 < len(chord_track) else False:
        add(drumsR, swell(BAR), t0)
    if label == 'Bridge' and idx + 1 < len(chord_track) and chord_track[idx + 1][4] != 'Bridge':
        add(drumsR, swell(BAR), t0, 1.4)
        for k in range(4):
            add(drums, SN, t0 + 2 * BEAT + k * BEAT / 2, 0.25 + 0.12 * k)

if os.environ.get('VOCAL', 'sung') == 'sung':
    from sing import Singer
    singer = Singer(LANG, syllables)
prev = None
for start, end, text, label, notes in lyric_track:
    vel = {'Verse 1': 0.75, 'Verse 2': 0.85, 'Chorus': 1.0, 'Final Chorus': 1.1,
           'Bridge': 0.95, 'Outro': 0.7}.get(label, 0.9)
    if os.environ.get('VOCAL', 'sung') == 'sung':
        y, t0 = singer.line(text, notes)
        add(vox, y, t0, vel)
        if 'Chorus' in label:  # two looser double-tracks, panned
            for buf in (vox2, vox3):
                y2, t2 = singer.line(text, notes, breath=False)
                add(buf, y2, t2, vel)
        continue
    for t, d, m, v in notes:
        add(vox, voice(m, d, v, prev, vel), t)
        prev = m
    prev = None

print('mixing')


def norm(x):
    p = np.max(np.abs(x))
    return x / p if p > 0 else x


pianoL, pianoR = norm(pianoL) * 0.55, norm(pianoR) * 0.55
padL, padR = norm(padL) * 0.35, norm(padR) * 0.35
bassB = norm(bassB) * 0.45
drums, drumsR = norm(drums) * 0.45, norm(drumsR) * 0.3
def movavg(x, n):
    c = np.cumsum(np.concatenate([[0.0], x]))
    y = (c[n:] - c[:-n]) / n
    return np.concatenate([np.full(n // 2, y[0]), y, np.full(len(x) - len(y) - n // 2, y[-1])])


def comp(x, thr=0.3, ratio=3.0):
    n = int(0.03 * SR)
    env = np.sqrt(movavg(x ** 2, n)) + 1e-9
    e = env / np.max(env)
    return x * movavg(np.where(e > thr, (e / thr) ** (1 / ratio - 1), 1.0), n)


vox, vox2, vox3 = comp(vox), comp(vox2 + 1e-9), comp(vox3 + 1e-9)
vpk = np.max(np.abs(vox)) + 1e-9
vox, vox2, vox3 = vox / vpk * 0.62, vox2 / vpk * 0.62, vox3 / vpk * 0.62

instL = pianoL * 0.75 + pianoR * 0.25 + padL + bassB + drums + drumsR * 0.4
instR = pianoR * 0.75 + pianoL * 0.25 + padR + bassB + drums + drumsR * 0.6
sendL = pianoL * 0.25 + padL * 0.4 + drums * 0.12
sendR = pianoR * 0.25 + padR * 0.4 + drums * 0.12
revL, revR = reverb(sendL, seed=1), reverb(sendR, seed=2)
vrevL, vrevR = reverb(vox + 0.3 * (vox2 + vox3), 2.6, 3), reverb(vox + 0.3 * (vox2 + vox3), 2.6, 4)
# simple slap delay on vocal
dly = int(BEAT * 0.75 * SR)
vdl = np.concatenate([np.zeros(dly), vox[:-dly]]) * 0.12


def master(L, R):
    st = np.stack([L, R], 1)
    st /= np.max(np.abs(st)) + 1e-9
    st = np.tanh(st * 1.6) / np.tanh(1.6)
    fade = int(3 * SR)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return st * 0.93


inst = master(instL + revL * 0.5, instR + revR * 0.5)
full = master(instL + revL * 0.5 + vox + 0.3 * vox2 + 0.12 * vox3 + vrevL * 0.35 + vdl,
              instR + revR * 0.5 + vox + 0.3 * vox3 + 0.12 * vox2 + vrevR * 0.35 + vdl)


def write_wav(path, st):
    data = (st * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())


tmp = os.path.join(OUT, f'_tmp_{SLUG}')
os.makedirs(tmp, exist_ok=True)
write_wav(f'{tmp}/full.wav', full)
write_wav(f'{tmp}/inst.wav', inst)
for src, name in (('full', f'{SLUG}-demo.mp3'), ('inst', f'{SLUG}-karaoke.mp3')):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{tmp}/{src}.wav',
                    '-b:a', '192k', os.path.join(OUT, name)], check=True)

# ---------------------------------------------------------------- lyric video

print('rendering video')
W, H, FPS = 1280, 720, 15
F_BIG = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
F_REG = '/usr/share/fonts/opentype/inter/Inter-Regular.otf'
F_TH = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
for f in (F_BIG, F_REG, F_TH):
    if not os.path.exists(f):
        F_BIG = F_REG = F_TH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        break
font_cache = {}


def font(path, size):
    if (path, size) not in font_cache:
        font_cache[(path, size)] = ImageFont.truetype(path, size)
    return font_cache[(path, size)]


yy, xx = np.mgrid[0:H, 0:W]


def background(c1, c2):
    g = (yy / H)[..., None]
    img = np.array(c1)[None, None] * (1 - g) + np.array(c2)[None, None] * g
    vign = 1 - 0.55 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)[..., None]
    return Image.fromarray(np.clip(img * vign, 0, 255).astype(np.uint8))


BGS = {
    0: background((18, 16, 38), (6, 6, 14)),
    1: background((20, 24, 52), (8, 8, 20)),
    2: background((44, 22, 64), (10, 8, 24)),
    3: background((78, 26, 70), (16, 8, 30)),
    4: background((110, 40, 60), (24, 10, 34)),
}
SEC_ENERGY = {s[0]: s[4] for s in SECTIONS}
orbs = [(rng.random() * W, rng.random() * H, 30 + rng.random() * 90, rng.random() * 6.28,
         0.05 + rng.random() * 0.1) for _ in range(14)]


def fit(text, path, size, maxw):
    while size > 20:
        f = font(path, size)
        if f.getlength(text) <= maxw:
            return f
        size -= 2
    return font(path, size)


def line_progress(notes, t):
    if not notes or t < notes[0][0]:
        return 0.0
    k = sum(1 for n in notes if n[0] <= t)
    s, d = notes[k - 1][0], notes[k - 1][1]
    return min(1.0, (k - 1 + min(1, (t - s) / max(d, 1e-3))) / len(notes))


ff = subprocess.Popen(
    ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
     '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', f'{tmp}/full.wav',
     '-c:v', 'libx264', '-preset', 'medium', '-crf', '26', '-pix_fmt', 'yuv420p',
     '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart',
     os.path.join(OUT, f'{SLUG}-lyric-video.mp4')],
    stdin=subprocess.PIPE)

nframes = int(SONG_LEN * FPS)
for fi in range(nframes):
    t = fi / FPS
    cur_i = None
    for i, (s, e, *_r) in enumerate(lyric_track):
        if s - 0.4 <= t < e:
            cur_i = i
    section = 'Intro'
    for (t0, c, tr, en, label, first) in chord_track:
        if t0 <= t:
            section = label
    energy = SEC_ENERGY[section]
    img = BGS[energy].copy()
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for (ox, oy, r, ph, sp) in orbs:
        x = (ox + 18 * np.sin(t * sp * 2 + ph) + t * 6 * sp * 10) % (W + 200) - 100
        y = oy + 22 * np.cos(t * sp + ph)
        a = int(16 + 14 * (energy / 4) + 10 * np.sin(t * 0.8 + ph))
        od.ellipse([x - r, y - r, x + r, y + r], fill=(255, 190, 220, a))
    img = Image.alpha_composite(img.convert('RGBA'), ov)
    d = ImageDraw.Draw(img)
    d.text((40, 30), TITLE.upper(), font=font(F_BIG, 22), fill=(255, 255, 255, 200))
    d.text((W - 40, 30), section.upper(), font=font(F_REG, 20), fill=(255, 210, 230, 190), anchor='ra')

    first_vocal = lyric_track[0][0]
    if t < first_vocal - 0.5:
        a = int(255 * min(1, t / 1.5, (first_vocal - 0.5 - t) / 1.0))
        d.text((W / 2, H / 2 - 30), TITLE, font=font(F_TH, 84), fill=(255, 255, 255, a), anchor='mm')
        d.text((W / 2, H / 2 + 45), 'original hugot ballad  ·  lyric video', font=font(F_REG, 24),
               fill=(255, 210, 230, a), anchor='mm')
    elif cur_i is not None:
        s, e, text, label, notes = lyric_track[cur_i]
        fbig = fit(text, F_BIG, 58, W - 140)
        p = line_progress(notes, t)
        tw = fbig.getlength(text)
        x0 = (W - tw) / 2
        y0 = H / 2 - 20
        d.text((x0, y0), text, font=fbig, fill=(255, 255, 255, 110), anchor='lm')
        if p > 0:
            hl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            hd = ImageDraw.Draw(hl)
            hd.text((x0, y0), text, font=fbig, fill=(255, 225, 120, 255), anchor='lm')
            mask = Image.new('L', (W, H), 0)
            ImageDraw.Draw(mask).rectangle([0, 0, x0 + tw * p, H], fill=255)
            img.paste(hl, (0, 0), Image.composite(hl, Image.new('RGBA', (W, H)), mask).split()[3])
        if cur_i > 0 and lyric_track[cur_i - 1][1] > s - BAR * 2:
            pt = lyric_track[cur_i - 1][2]
            d.text((W / 2, y0 - 80), pt, font=fit(pt, F_REG, 32, W - 160), fill=(255, 255, 255, 70), anchor='mm')
        if cur_i + 1 < len(lyric_track) and lyric_track[cur_i + 1][0] < e + BAR * 2:
            nt = lyric_track[cur_i + 1][2]
            d.text((W / 2, y0 + 85), nt, font=fit(nt, F_REG, 32, W - 160), fill=(255, 255, 255, 120), anchor='mm')
    else:
        last = lyric_track[-1][1]
        if t > last:
            a = int(255 * min(1, (t - last) / 1.2))
            d.text((W / 2, H / 2), END_MSG, font=font(F_REG, 32),
                   fill=(255, 225, 120, a), anchor='mm')
    # progress bar
    d.rectangle([40, H - 34, W - 40, H - 31], fill=(70, 50, 80))
    d.rectangle([40, H - 34, 40 + (W - 80) * t / SONG_LEN, H - 31], fill=(255, 190, 220, 200))
    mm, ss = divmod(int(t), 60)
    d.text((40, H - 58), f'{mm}:{ss:02d}', font=font(F_REG, 16), fill=(255, 255, 255, 140))
    ff.stdin.write(img.convert('RGB').tobytes())
    if fi % 600 == 0:
        print(f'  frame {fi}/{nframes}')
ff.stdin.close()
ff.wait()
for f in os.listdir(tmp):
    os.remove(os.path.join(tmp, f))
os.rmdir(tmp)
print('done')

"""Builds the organized delivery folder (print files by subsystem, report PDF,
deck template, software, renders, CAD source).

    python tools/make_package.py      (from trash-sorter-boat/, after cad/build.py)
"""
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.abspath(os.path.join(SRC, "..", "TRASH_SORTER_BOAT_PACKAGE"))
sys.path.insert(0, os.path.join(SRC, "cad"))
import common as C  # noqa: E402

PARTS = json.load(open(os.path.join(SRC, "cad", "parts.json")))
INFO = {p["part"]: p for p in PARTS["parts"]}

# folder -> [(stl name, qty in this folder, note)]
GROUPS = {
    "1_Hull": [("pontoon_bow_port", 1, ""), ("pontoon_bow_stbd", 1, ""), ("pontoon_mid", 4, "two per side"),
               ("pontoon_stern_port", 1, ""), ("pontoon_stern_stbd", 1, ""), ("dowel", 8, "segment joints"),
               ("motor_saddle", 4, "clamps the drive motors")],
    "2_Drive_Wheels": [("paddle_wheel", 4, "")],
    "3_Intake_Conveyor": [("c1_frame_lower", 1, ""), ("c1_frame_upper", 1, ""), ("c1_splice", 2, ""),
                          ("c1_leg_port", 1, ""), ("c1_leg_stbd", 1, ""), ("drum_drive", 1, "top drum"),
                          ("drum_idler", 1, "bottom drum"), ("belt_link", C.LINKS_C1 - C.LINKS_C1 // C.CLEAT_EVERY, ""),
                          ("belt_link_cleat", C.LINKS_C1 // C.CLEAT_EVERY, "every 4th link")],
    "4_Sorting_Conveyor": [("c2_front_frame", 1, "camera zone + chute"), ("c2_bed_beam_front", 1, ""), ("c2_bed_beam_rear", 1, ""),
                           ("c2_head_stand_drive", 1, "port"), ("c2_head_stand_idler", 1, "starboard"),
                           ("drum_drive", 1, "stern drum"), ("drum_idler", 1, "front drum"),
                           ("belt_link", C.LINKS_C2, ""), ("reject_tray", 1, "")],
    "5_Sorter_Bins": [("sorter_frame_front_port", 1, "bin 1"), ("sorter_frame_front_stbd", 1, "bin 2"),
                      ("sorter_frame_rear_port", 1, "bin 3"), ("sorter_frame_rear_stbd", 1, "bin 4"),
                      ("sorter_cover_front_port", 1, "bin 1"), ("sorter_cover_front_stbd", 1, "bin 2"),
                      ("sorter_cover_rear_port", 1, "bin 3"), ("sorter_cover_rear_stbd", 1, "bin 4"), ("servo_bridge", 4, ""),
                      ("flap_port", 2, "bins 1 + 3"), ("flap_stbd", 2, "bins 2 + 4"), ("bucket", 4, "")],
    "6_Electronics_Mounts": [("electronics_box", 1, "port bow deck"), ("battery_box", 1, "starboard bow deck"),
                             ("box_lid", 2, ""), ("camera_mast", 1, "sorting camera + LEDs"),
                             ("nav_cam_bracket", 1, "front webcam")],
}
SETTINGS = {"1_Hull": "PLA/PETG, 3 walls, 5 top + 5 bottom, 5% gyroid, no supports",
            "2_Drive_Wheels": "3 walls, 20% infill, flange down",
            "3_Intake_Conveyor": "2-3 walls, 15% infill; belt links on edge as exported",
            "4_Sorting_Conveyor": "2-3 walls, 15% infill; belt links on edge as exported",
            "5_Sorter_Bins": "2-3 walls, 15% infill",
            "6_Electronics_Mounts": "2-3 walls, 15% infill"}


def build_print_files():
    base = os.path.join(OUT, "02_Print_Files")
    rows = []
    for folder, items in GROUPS.items():
        d = os.path.join(base, folder)
        os.makedirs(d, exist_ok=True)
        for i, (name, qty, note) in enumerate(items, 1):
            fn = f"{i:02d}_{name}__x{qty}.stl"
            shutil.copy(os.path.join(SRC, "stl", name + ".stl"), os.path.join(d, fn))
            p = INFO[name]
            g = p["grams_each"] * qty
            rows.append([folder, fn, qty, " x ".join(f"{v:.0f}" for v in p["size"]), round(g), SETTINGS[folder], note])
    with open(os.path.join(base, "Print_List.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["folder", "file", "qty", "size_mm", "filament_g_total", "settings", "note"])
        w.writerows(rows)
    return rows


def section(md, title_start):
    """Text of the README section whose heading starts with title_start (without the heading)."""
    m = re.search(r"^## " + re.escape(title_start) + r".*?$\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def img(name, caption):
    return f'<figure><img src="file://{os.path.join(SRC, "renders", name)}"><figcaption>{caption}</figcaption></figure>'


def report_markdown(rows):
    md = open(os.path.join(SRC, "README.md")).read()
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)\n?", "", md)                          # images are placed by hand below
    d = PARTS
    links = C.LINKS_C1 + C.LINKS_C2
    lwl, b, yc = C.BOAT_L - 30.0, C.P_W, C.P_CY
    I = 2 * (lwl * b ** 3 / 12 + lwl * b * yc ** 2)
    V = d["dry_mass_g"] * 1000.0
    BM, KB, KG = I / V, d["draft_mm_dry"] / 2, 140.0
    belt_v = C.TEETH * C.PITCH * 30 / 60
    groups = {}
    for r in rows:
        groups.setdefault(r[0], [0, 0])
        groups[r[0]][0] += r[2]
        groups[r[0]][1] += r[4]
    ptab = "\n".join(f"| `{g}` | {n} | {gr} | {SETTINGS[g]} |" for g, (n, gr) in groups.items())
    parts_tab = "\n".join(f"| {r[0].split('_', 1)[1].replace('_', ' ')} | `{r[1]}` | {r[2]} | {r[3]} | {r[4]} | {r[6]} |" for r in rows)
    sec = {}
    sec["summary"] = f"""This report describes an affordable, 3D-printed amphibious boat. A conveyor at the bow collects floating trash. A camera on a second conveyor identifies each item, and a servo-driven door sorts it into one of 4 bins. It drives on land and in water on 4 paddle wheels, and it is steered from a phone with a live navigation camera.

The design was modelled parametrically and checked in software: no parts overlap, every part fits a 220 × 220 mm printer bed, and the buoyancy was computed from the hull shape. Estimated materials cost is **≈ ₱13,710**, and **{d['filament_g'] / 1000:.1f} kg** of filament prints **{sum(r[2] for r in rows)} parts**."""
    sec["calc"] = f"""### Buoyancy and draft
The boat sinks until the water it pushes aside weighs as much as the boat (m = ρ·V). The waterline was found from the CAD pontoon volume by bisection.

| Load | Mass (g) | Draft (mm) |
|---|---|---|
| Dry | {d['dry_mass_g']} | {d['draft_mm_dry']} |
| With 500 g of trash | {d['dry_mass_g'] + 500} | {d['draft_mm_with 500 g trash']} |
| Maximum (water at the deck) | {d['max_displacement_g']} | {C.P_H:.0f} |

Reserve buoyancy is {(d['max_displacement_g'] - d['dry_mass_g'] - 500) / (d['dry_mass_g'] + 500) * 100:.0f}% at full load. The drive-motor pockets start at z = {C.POCKET_FLOOR:.0f} mm, which stays above the waterline.

### Stability
GM = KB + BM − KG, with BM = I_T / V.

For the two pontoons (waterline length ≈ {lwl:.0f} mm, width {b:.0f} mm, pontoon centres at ±{yc:.1f} mm): I_T ≈ {I:.3g} mm⁴, so BM ≈ {BM:.0f} mm. With KB ≈ {KB:.0f} mm and an estimated KG ≈ {KG:.0f} mm, **GM ≈ {KB + BM - KG:.0f} mm**. That is a very stable boat: the wide pontoon spacing dominates.

### Belt speed and sorting geometry
- **Belt speed:** each sprocket turn moves the belt {C.TEETH} teeth × {C.PITCH:.0f} mm = {C.TEETH * C.PITCH:.0f} mm. At 30 rpm that is {belt_v:.0f} mm/s, so about {belt_v * 0.8:.0f} mm/s (intake) and {belt_v * 0.7:.0f} mm/s (sorting) at the PWM settings used.
- **Belts:** {links} printed links in total (intake {C.LINKS_C1}, sorting {C.LINKS_C2}). The sprocket pitch radius is {C.R_PIN:.2f} mm.
- **Doors:** each door is {C.FLAP_L:.1f} mm long and swings {60}° across the {C.BELT_W:.0f} mm belt. It stops about 1 mm short of the far edge and about 3 mm short of the opposite closed door, checked in the CAD assembly.

### Power and run time
- Wheel motors: about 4 × 0.25 A.
- Conveyors: about 2 × 0.2 A.
- Pi Zero 2 W, both cameras and the LED strip: about 0.4 A at 12 V.
- Servos, idle: about 0.05 A.

That totals about **1.9 A** average. A 3S1P pack of 2.5 Ah cells gives **about 1 h** of run time, allowing for losses (about 2 h with a 3S2P pack)."""
    sec["parts"] = f"""Files are in `02_Print_Files/`, one folder per subsystem. Each file name ends with the number of copies to print (`__x2`). `Print_List.csv` has the full list. No part needs supports.

| Folder | Copies | Filament (g) | Settings |
|---|---|---|---|
{ptab}

| Subsystem | File | Qty | Size (mm) | g | Note |
|---|---|---|---|---|---|
{parts_tab}"""
    sec["tests"] = """| Test | Method | Pass criterion |
|---|---|---|
| T1 Leak | Hold each pontoon segment under water for 60 s, then weigh it. Float the full boat for 10 min | No bubble stream; mass gain < 5 g; boxes dry |
| T2 Draft and stability | Float the boat with 500 g of trash and measure the draft. Press one side down 20° | Draft within ±5 mm of the computed value; self-rights |
| T3 Collection | Release 20 floating items in front of the bow while driving slowly | ≥ 16 of 20 reach the sorting belt |
| T4 Sorting accuracy | Run 10 items of each class through the sorter | ≥ 80% end up in the correct bin |
| T5 Water and land speed | Time a 3 m run in water, then on concrete | ≥ 0.2 m/s in water; ≥ 0.4 m/s on land |
| T6 Land–water transition | Drive out of the water up a 15° ramp and back in | Completes both ways without help |
| T7 Failsafe and endurance | Turn the phone's Wi-Fi off while driving; then run until the battery is flat | Drive stops within 1 s; run time ≥ 45 min |

**Scoring rubric (each criterion 1–4):**

| Criterion | Weight |
|---|---|
| Buoyancy and stability | 15% |
| Trash collection rate | 20% |
| Sorting accuracy | 20% |
| Mobility on land and water | 15% |
| Cost efficiency | 10% |
| Documentation | 20% |"""
    sec["verify"] = f"""**Checked in software:**
- Interference check of all 73 assembly parts: 0 overlaps, with a door open and with all doors closed.
- All {len(d['parts'])} STL files are watertight meshes and fit a 220 × 220 × 250 mm bed.
- The sorting logic passes its unit tests, and the phone dashboard runs in mock mode.

**Limits:**
- The boat has not been printed or tested. Masses, speeds and run time are estimates.
- The motor face-hole spacing differs by brand, so measure your motors first.
- The official OCNR guidelines were not available. The design follows the brief given by the team.
- Prices are approximate Philippine online prices (October 2026). Check them with the suppliers."""
    parts_md = f"""# Affordable Trash-Collecting and Sorting Amphibious Boat

<div class="sub">Design report · {datetime.date.today():%B %Y}</div>

{img("01_hero_front.png", "Figure 1. Assembled boat: bow intake conveyor, electronics boxes, sorting conveyor and bins.")}

## 1. Summary
{sec['summary']}

## 2. Design requirements
{section(md, '2. Guidelines used')}

## 3. How it works
{section(md, '1. How it works')}

{img("07_intake_closeup.png", "Figure 2. Cleated intake conveyor between the pontoons.")}
{img("06_sorter_closeup.png", "Figure 3. Sorting conveyor with one bin door open (covers hidden).")}

## 4. Specifications
{section(md, '3. Specifications')}

{img("04_side_afloat.png", "Figure 4. Side view at the computed waterline.")}
{img("03_top_plan.png", "Figure 5. Plan view.")}

## 5. Engineering calculations
{sec['calc']}

## 6. Materials list and suppliers
{section(md, '4. Materials list')}

## 7. Printed parts
{sec['parts']}

## 8. Assembly
{section(md, '6. Assembly')}

## 9. Wiring
{section(md, '7. Wiring')}

## 10. Software and camera training
{section(md, '8. Software')}

## 11. Test plan and assessment
{sec['tests']}

## 12. Safety
{section(md, '9. Safety')}

## 13. Verification and limitations
{sec['verify']}

## References
1. Halliday, Resnick & Walker. *Fundamentals of Physics* (Archimedes' principle).
2. Tupper, E. C. *Introduction to Naval Architecture* (metacentric height).
3. Google Teachable Machine, teachablemachine.withgoogle.com (image classification, TensorFlow Lite export).
4. Raspberry Pi Ltd. Raspberry Pi Zero 2 W and Camera Module documentation.
5. MakerLab Electronics, makerlab.ph; Circuitrocks, circuit.rocks (component sources).
"""
    return parts_md


CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #1d232a; }
h1 { font-size: 24pt; margin: 0 0 4pt; color: #12406b; }
.sub { color: #5b6672; margin-bottom: 14pt; font-size: 11pt; }
h2 { font-size: 15pt; color: #12406b; border-bottom: 2px solid #12406b; padding-bottom: 3pt; margin-top: 22pt; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.6pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: #12406b; color: #fff; text-align: left; padding: 4pt 5pt; }
td { border-bottom: 1px solid #d6dbe0; padding: 3pt 5pt; vertical-align: top; }
tr:nth-child(even) td { background: #f4f6f8; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.2pt; background: #eef1f4; padding: 0 2pt; border-radius: 2pt; }
pre { background: #eef1f4; padding: 6pt; font-size: 8.2pt; white-space: pre-wrap; }
figure { margin: 8pt 0 12pt; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; max-height: 105mm; border: 1px solid #d6dbe0; }
figcaption { font-size: 8.6pt; color: #5b6672; margin-top: 3pt; }
h2:nth-of-type(n+5) { page-break-before: auto; }
"""


def fix_lists(md):
    """Python-Markdown needs a blank line before a list and 4-space nesting."""
    out, prev = [], ""
    item = re.compile(r"^\s*([-*]|\d+\.)\s")
    for line in md.split("\n"):
        m = re.match(r"^( {2,3})([-*]|\d+\.)\s", line)
        if m:
            line = "    " + line.lstrip()
        if item.match(line) and prev.strip() and not item.match(prev) and not prev.startswith("    ") and not prev.startswith("|"):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def build_report(rows):
    d = os.path.join(OUT, "01_Report")
    os.makedirs(d, exist_ok=True)
    html = markdown.markdown(fix_lists(report_markdown(rows)), extensions=["tables", "fenced_code"])
    html_path = os.path.join(d, "report.html")
    with open(html_path, "w") as f:
        f.write(f"<!doctype html><html><head><meta charset='utf-8'><title>Trash Sorter Boat Report</title><style>{CSS}</style></head><body>{html}</body></html>")
    pdf = os.path.join(d, "Trash_Sorter_Boat_Report.pdf")
    subprocess.run(["node", os.path.join(HERE, "html2pdf.mjs"), html_path, pdf], check=True)
    os.remove(html_path)
    return pdf


def copy_rest():
    shutil.copytree(os.path.join(SRC, "deck"), os.path.join(OUT, "03_Deck_Cutting_Template"), dirs_exist_ok=True)
    shutil.copytree(os.path.join(SRC, "software"), os.path.join(OUT, "04_Software"), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    r = os.path.join(OUT, "05_Renders")
    os.makedirs(r, exist_ok=True)
    for f in os.listdir(os.path.join(SRC, "renders")):
        shutil.copy(os.path.join(SRC, "renders", f), r)
    shutil.copy(os.path.join(SRC, "stl", "assembly_preview_DO_NOT_PRINT.stl"), r)
    c = os.path.join(OUT, "06_CAD_Source")
    os.makedirs(c, exist_ok=True)
    for f in os.listdir(os.path.join(SRC, "cad")):
        if f.endswith((".py", ".json")):
            shutil.copy(os.path.join(SRC, "cad", f), c)


START = """TRASH-SORTING AMPHIBIOUS BOAT - PACKAGE
=========================================
01_Report/                Trash_Sorter_Boat_Report.pdf - full design report (read this first)
02_Print_Files/           STL files to print, one folder per subsystem.
                          File names end with the number of copies (e.g. __x4 = print 4).
                          Print_List.csv = every file, quantity, size, filament, settings.
03_Deck_Cutting_Template/ deck_template_1to1.svg (print at 100 %, trace on 5 mm Sintra)
                          deck_5mm_pvc.dxf (for a CNC shop; never laser-cut PVC)
04_Software/              Raspberry Pi Zero 2 W code: run setup.sh on the Pi
05_Renders/               pictures, assembly.glb (3D view) and the assembled model (viewing only)
06_CAD_Source/            parametric Python CAD; python build.py regenerates everything

Total to print: {n} parts, about {kg:.1f} kg of filament. No supports needed. Fits a 220 x 220 mm bed.
"""


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    rows = build_print_files()
    copy_rest()
    pdf = build_report(rows)
    with open(os.path.join(OUT, "00_START_HERE.txt"), "w") as f:
        f.write(START.format(n=sum(r[2] for r in rows), kg=PARTS["filament_g"] / 1000))
    print("package:", OUT, "| report:", os.path.getsize(pdf) // 1024, "KB")


if __name__ == "__main__":
    main()

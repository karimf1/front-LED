#!/usr/bin/env python3
"""
verify_model.py -- independent check of the front LED light-bar holder.

Rebuilds the same solids that front_led_mount.lsp builds in AutoCAD, but
with an open-source CSG kernel (trimesh + manifold3d), then:

  * confirms every part is a closed, watertight solid
  * confirms no two parts interfere
  * reports volume and mass per part
  * runs the beam check that drove the choice of rail section
  * optionally writes an STL per part  (--stl DIR)

    python3 verify_model.py
    python3 verify_model.py --stl ../exports/stl

Requires: trimesh, manifold3d, numpy, scipy
"""
import argparse
import itertools
import math
import os

import numpy as np
import trimesh
from trimesh.creation import box as _box, cylinder as _cyl

from params import P, BORE_R, RAIL_H_EFF, MOUNT_SPAN, CLAMP_SPAN

SECTIONS = 96          # facets per cylinder


# --------------------------------------------------------------- primitives
def box(cx, cy, cz, lx, ly, lz):
    m = _box(extents=(lx, ly, lz))
    m.apply_translation((cx, cy, cz))
    return m


def cylz(cx, cy, z0, r, h):
    m = _cyl(radius=r, height=abs(h), sections=SECTIONS)
    m.apply_translation((cx, cy, z0 + h / 2.0))
    return m


def cylx(x0, x1, cy, cz, r):
    m = _cyl(radius=r, height=abs(x1 - x0), sections=SECTIONS)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    m.apply_translation(((x0 + x1) / 2.0, cy, cz))
    return m


def sub(base, tools):
    for t in tools:
        base = trimesh.boolean.difference([base, t], engine="manifold")
    return base


# ------------------------------------------------------------------- parts
def rail():
    h = RAIL_H_EFF
    body = box(0, 0, -h / 2, P["RAIL_LEN"], P["RAIL_W"], h)
    tools = []
    if P["RAIL_SECTION"] == "TUBE":
        tools.append(box(0, 0, -h / 2, P["RAIL_LEN"] + 40,
                         P["RAIL_W"] - 2 * P["RAIL_T"], h - 2 * P["RAIL_T"]))
    for sx in (-1, 1):
        for x in (P["PLATE_CTR_X"] - P["PLATE_PITCH"] / 2,
                  P["PLATE_CTR_X"] + P["PLATE_PITCH"] / 2):
            tools.append(cylz(sx * x, 0, 20, P["PLATE_HOLE_D"] / 2, -(h + 60)))
        for y in (-P["CBOLT_Y"], P["CBOLT_Y"]):
            tools.append(cylz(sx * P["CLAMP_X"], y, 20, P["CBOLT_D"] / 2, -(h + 60)))
    return sub(body, tools)


def plate(sx):
    cx = sx * P["PLATE_CTR_X"]
    zc = -RAIL_H_EFF - P["PLATE_T"] / 2
    body = box(cx, 0, zc, P["PLATE_LEN"], P["PLATE_W"], P["PLATE_T"])
    tools = [cylz(x, 0, zc + 20, P["PLATE_HOLE_D"] / 2, -60)
             for x in (cx - P["PLATE_PITCH"] / 2, cx + P["PLATE_PITCH"] / 2)]
    return sub(body, tools)


def saddle(sx):
    cx = sx * P["CLAMP_X"]
    body = box(cx, 0, P["SADDLE_H"] / 2, P["CLAMP_L"], P["CLAMP_W"], P["SADDLE_H"])
    tools = [cylx(cx - P["CLAMP_L"], cx + P["CLAMP_L"], 0, P["SADDLE_H"], BORE_R)]
    for y in (-P["CBOLT_Y"], P["CBOLT_Y"]):
        tools.append(cylz(cx, y, P["SADDLE_H"] + 10, P["CBOLT_D"] / 2,
                          -(P["SADDLE_H"] + 20)))
    return sub(body, tools)


def strap(sx):
    cx = sx * P["CLAMP_X"]
    body = box(cx, 0, P["SADDLE_H"] + P["STRAP_H"] / 2,
               P["CLAMP_L"], P["CLAMP_W"], P["STRAP_H"])
    tools = [cylx(cx - P["CLAMP_L"], cx + P["CLAMP_L"], 0, P["SADDLE_H"], BORE_R)]
    for y in (-P["CBOLT_Y"], P["CBOLT_Y"]):
        tools.append(cylz(cx, y, P["SADDLE_H"] + P["STRAP_H"] + 10,
                          P["CBOLT_D"] / 2, -(P["STRAP_H"] + 20)))
    return sub(body, tools)


def crush(cx, cy, od, idd):
    z0 = -P["RAIL_T"]
    hh = -(P["RAIL_H"] - 2 * P["RAIL_T"])
    return sub(cylz(cx, cy, z0, od / 2, hh), [cylz(cx, cy, z0 + 5, idd / 2, hh - 10)])


def bar():
    return cylx(-P["BAR_LEN"] / 2, P["BAR_LEN"] / 2, 0, P["SADDLE_H"], P["BAR_D"] / 2)


def build():
    parts = {"rail": [rail()],
             "plate": [plate(s) for s in (-1, 1)],
             "saddle": [saddle(s) for s in (-1, 1)],
             "strap": [strap(s) for s in (-1, 1)]}
    cr = []
    for sx in (-1, 1):
        for x in (P["PLATE_CTR_X"] - P["PLATE_PITCH"] / 2,
                  P["PLATE_CTR_X"] + P["PLATE_PITCH"] / 2):
            cr.append(crush(sx * x, 0, P["CRUSH_OD_M10"], P["PLATE_HOLE_D"]))
        for y in (-P["CBOLT_Y"], P["CBOLT_Y"]):
            cr.append(crush(sx * P["CLAMP_X"], y, P["CRUSH_OD_M6"], P["CBOLT_D"]))
    parts["crush"] = cr
    parts["bar"] = [bar()]
    return parts


# -------------------------------------------------------------- beam check
def I_flat(b, h):
    return b * h ** 3 / 12.0


def I_tube(b, h, t):
    return (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12.0


def A_tube(b, h, t):
    return b * h - (b - 2 * t) * (h - 2 * t)


def beam_case(name, I, A, ymax):
    """Simply supported at the two chassis plates, two clamp loads inboard."""
    g, E = 9.81, P["E_AL"]
    L = MOUNT_SPAN                       # 1700
    a = (MOUNT_SPAN - CLAMP_SPAN) / 2    # 550, support -> clamp
    m = A * P["RAIL_LEN"] * P["DENS"] / 1000.0        # kg
    w = m * g / P["RAIL_LEN"]                          # N/mm, self weight
    F = P["BAR_MASS"] * g / 2.0                        # N per clamp
    d = F * a * (3 * L ** 2 - 4 * a ** 2) / (24 * E * I) + 5 * w * L ** 4 / (384 * E * I)
    sig = (F * a + w * L ** 2 / 8.0) * ymax / I
    mu = (m + P["BAR_MASS"]) / (P["RAIL_LEN"] / 1000.0)
    f1 = (math.pi / 2) * math.sqrt((E * 1e6 * I * 1e-12) / (mu * (L / 1000.0) ** 4))
    return dict(name=name, I=I, mass=m, delta=d, ratio=L / d, sigma=sig, f1=f1)


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stl", metavar="DIR", help="write one STL per part")
    args = ap.parse_args()

    parts = build()

    print("=" * 74)
    print("  SOLID VALIDITY AND MASS")
    print("=" * 74)
    print(f"  {'part':10s} {'qty':>3s} {'volume cm3':>12s} {'mass kg':>9s}   watertight")
    al_total = 0.0
    steel_total = 0.0
    for k, v in parts.items():
        vol = sum(m.volume for m in v) / 1000.0
        dens = P["DENS_STEEL"] if k == "crush" else P["DENS"]
        mass = vol * dens
        ok = all(m.is_watertight for m in v)
        print(f"  {k:10s} {len(v):3d} {vol:12.1f} {mass:9.3f}   {ok}")
        if k == "crush":
            steel_total += mass
        elif k != "bar":
            al_total += mass
    print(f"\n  aluminium (6061-T6) .......... {al_total:6.3f} kg")
    print(f"  stainless crush tubes ........ {steel_total:6.3f} kg")
    print(f"  FABRICATED ASSEMBLY .......... {al_total + steel_total:6.3f} kg"
          f"   (light bar and fasteners excluded)")

    print("\n" + "=" * 74)
    print("  INTERFERENCE CHECK")
    print("=" * 74)
    flat = [(f"{k}{i+1}", m) for k, v in parts.items() for i, m in enumerate(v)]
    bad = 0
    for (na, a), (nb, b) in itertools.combinations(flat, 2):
        amin, amax = a.bounds
        bmin, bmax = b.bounds
        if np.any(amax < bmin + 1e-9) or np.any(bmax < amin + 1e-9):
            continue
        inter = trimesh.boolean.intersection([a, b], engine="manifold")
        vol = inter.volume / 1000.0 if inter is not None and len(inter.faces) else 0.0
        if vol > 1e-4:
            print(f"  INTERFERENCE  {na} <-> {nb}: {vol:.2f} cm3")
            bad += 1
    print(f"  {bad} interfering pairs  ->  {'FAIL' if bad else 'PASS'}")

    allm = trimesh.util.concatenate([m for _, m in flat])
    lo, hi = allm.bounds
    print(f"\n  envelope  {hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} mm")

    print("\n" + "=" * 74)
    print(f"  RAIL SECTION STUDY   span {MOUNT_SPAN:.0f} mm, "
          f"clamps at {CLAMP_SPAN:.0f} mm centres, {P['BAR_MASS']} kg light bar")
    print("=" * 74)
    W = P["RAIL_W"]
    cases = [
        beam_case(f"FLAT {W:.0f} x 8   (as drawn)", I_flat(W, 8), W * 8, 4),
        beam_case(f"FLAT {W:.0f} x 10", I_flat(W, 10), W * 10, 5),
        beam_case(f"RHS  {W:.0f} x 30 x 3  <== USED", I_tube(W, 30, 3), A_tube(W, 30, 3), 15),
        beam_case(f"RHS  {W:.0f} x 40 x 3", I_tube(W, 40, 3), A_tube(W, 40, 3), 20),
    ]
    print(f"  {'section':26s} {'I mm4':>9s} {'kg':>6s} {'delta mm':>9s} "
          f"{'L/d':>7s} {'MPa':>6s} {'f1 Hz':>7s}")
    for c in cases:
        print(f"  {c['name']:26s} {c['I']:9.0f} {c['mass']:6.2f} {c['delta']:9.2f} "
              f"{c['ratio']:7.0f} {c['sigma']:6.1f} {c['f1']:7.1f}")
    print("\n  Stress is never the problem (all << 240 MPa yield).  The rail is")
    print("  STIFFNESS driven: the as-drawn flat bar sags ~16 mm and its first")
    print("  bending mode lands at ~5 Hz, inside the chassis excitation band.")
    print("  The 90x30x3 RHS costs no extra mass and fixes both.")

    if args.stl:
        os.makedirs(args.stl, exist_ok=True)
        for k, v in parts.items():
            for i, m in enumerate(v, 1):
                fn = os.path.join(args.stl, f"{k}_{i:02d}.stl")
                m.export(fn)
        print(f"\n  wrote {sum(len(v) for v in parts.values())} STL files to {args.stl}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
render_views.py -- shaded views of the assembly for the README.

Rasterises the verified CSG solids with a small z-buffer renderer, so the
images show correct occlusion without needing OpenGL or a display.

    python3 render_views.py [-o ../docs]
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

import verify_model as V

COL = {"rail": "#5b8cba", "plate": "#e8963f", "saddle": "#4da266",
       "strap": "#9ad3a8", "crush": "#606060", "bar": "#b45590"}
LIGHT = np.array([0.30, -0.78, 0.55])
LIGHT /= np.linalg.norm(LIGHT)


def basis(azim, elev):
    a, e = np.radians(azim), np.radians(elev)
    F = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    R = np.cross(F, [0, 0, 1.0])
    R /= np.linalg.norm(R)
    return R, np.cross(R, F), F


def crop(m, x0, x1):
    b = m.bounds
    if b[1][0] < x0 or b[0][0] > x1:
        return None
    if b[0][0] >= x0 and b[1][0] <= x1:
        return m
    slab = trimesh.creation.box(extents=(x1 - x0, 4000, 4000))
    slab.apply_translation(((x0 + x1) / 2.0, 0, 0))
    r = trimesh.boolean.intersection([m, slab], engine="manifold")
    return r if (r is not None and len(r.faces)) else None


def shift(parts, key, d):
    out = {}
    for k, ms in parts.items():
        if k == key:
            new = []
            for m in ms:
                m2 = m.copy()
                m2.apply_translation(d)
                new.append(m2)
            out[k] = new
        else:
            out[k] = ms
    return out


def render(parts, fname, azim, elev, xr=None, title="", W=1600, pad=0.04):
    R, U, F = basis(azim, elev)
    tris, cols = [], []
    for k, ms in parts.items():
        base = np.array(matplotlib.colors.to_rgb(COL[k]))
        for m in ms:
            if xr is not None:
                m = crop(m, *xr)
                if m is None:
                    continue
            N = m.face_normals
            vis = (N @ F) < 0
            t = m.vertices[m.faces[vis]]
            n = N[vis]
            if not len(t):
                continue
            tris.append(t)
            sh = np.clip(n @ LIGHT, 0, 1) * 0.60 + 0.40
            cols.append(np.clip(base[None, :] * sh[:, None], 0, 1))
    T, C = np.concatenate(tris), np.concatenate(cols)
    sx, sy, sz = T @ R, T @ U, T @ F
    xmn, xmx, ymn, ymx = sx.min(), sx.max(), sy.min(), sy.max()
    m_ = max(xmx - xmn, ymx - ymn) * pad
    xmn -= m_; xmx += m_; ymn -= m_; ymx += m_
    scale = W / (xmx - xmn)
    H = int(round((ymx - ymn) * scale))
    px, py = (sx - xmn) * scale, (ymx - sy) * scale
    zbuf = np.full((H, W), np.inf)
    img = np.ones((H, W, 3))
    x0 = np.clip(np.floor(px.min(1)).astype(int), 0, W - 1)
    x1 = np.clip(np.ceil(px.max(1)).astype(int), 0, W - 1)
    y0 = np.clip(np.floor(py.min(1)).astype(int), 0, H - 1)
    y1 = np.clip(np.ceil(py.max(1)).astype(int), 0, H - 1)
    for i in range(len(T)):
        ax_, ay_ = px[i, 0], py[i, 0]
        bx, by = px[i, 1], py[i, 1]
        cx, cy = px[i, 2], py[i, 2]
        den = (by - cy) * (ax_ - cx) + (cx - bx) * (ay_ - cy)
        if abs(den) < 1e-12:
            continue
        X = np.arange(x0[i], x1[i] + 1)
        Y = np.arange(y0[i], y1[i] + 1)
        if not len(X) or not len(Y):
            continue
        XX, YY = np.meshgrid(X + 0.5, Y + 0.5)
        l1 = ((by - cy) * (XX - cx) + (cx - bx) * (YY - cy)) / den
        l2 = ((cy - ay_) * (XX - cx) + (ax_ - cx) * (YY - cy)) / den
        l3 = 1.0 - l1 - l2
        msk = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not msk.any():
            continue
        z = l1 * sz[i, 0] + l2 * sz[i, 1] + l3 * sz[i, 2]
        sub = zbuf[Y[0]:Y[-1] + 1, X[0]:X[-1] + 1]
        upd = msk & (z < sub)
        if not upd.any():
            continue
        sub[upd] = z[upd]
        img[Y[0]:Y[-1] + 1, X[0]:X[-1] + 1][upd] = C[i]
    fig, ax = plt.subplots(figsize=(W / 170.0, H / 170.0 + (0.35 if title else 0)), dpi=170)
    fig.patch.set_facecolor("white")
    ax.imshow(img, interpolation="bilinear")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=11, color="#1a1a1a")
    plt.tight_layout()
    plt.savefig(fname, facecolor="white", bbox_inches="tight", dpi=170)
    plt.close()
    print("wrote", fname)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="../docs")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    p = V.build()
    o = lambda n: os.path.join(a.out, n)

    render(p, o("assembly-iso.png"), 235, 22, W=1900,
           title="Front LED light-bar holder – complete assembly (2000 × 90 × 110 mm)")
    render(shift(shift(p, "strap", [0, 0, 70]), "bar", [0, 0, 35]),
           o("clamp-exploded.png"), 215, 26, xr=(200, 400), W=1150,
           title="Clamp station, exploded – strap, Ø50 bar (Ø54 lined bore), saddle, crush tubes")
    render(p, o("clamp-assembled.png"), 215, 34, xr=(200, 400), W=1150,
           title="Clamp station, assembled")
    render(shift(p, "plate", [0, 0, -70]), o("mount-exploded.png"), 215, 26,
           xr=(720, 1000), W=1150,
           title="Chassis mount, exploded – 200×90×10 plate, 2 × M10 @ 120 pitch")


if __name__ == "__main__":
    main()

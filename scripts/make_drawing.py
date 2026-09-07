#!/usr/bin/env python3
"""
make_drawing.py  --  generate the A3 manufacturing drawing for the
front LED light-bar holder as a DXF that opens natively in AutoCAD.

    python3 make_drawing.py  [-o ../cad/front-led-mount-drawing.dxf]

The sheet is drawn 1:1 in millimetres in model space (A3, 420 x 297).
Each view is drawn at its own scale and its dimensions carry a DIMLFAC
override, so every dimension reads the TRUE size of the part.

Parameters are imported from params.py, which is the single source of
truth shared with front_led_mount.lsp.
"""
import argparse
import ezdxf
from ezdxf.enums import TextEntityAlignment

from params import P

# ---------------------------------------------------------------- sheet
SW, SH = 420.0, 297.0          # A3 landscape
M = 10.0                       # border margin

BORE_R = P["BAR_D"] / 2 + P["LINER_T"]
RAIL_H = P["RAIL_H"]


# ---------------------------------------------------------------- setup
def new_doc():
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 4          # millimetres
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2

    for name, color, lt in [
        ("SHEET",      7,   "Continuous"),
        ("TITLE",      7,   "Continuous"),
        ("OUTLINE",    7,   "Continuous"),
        ("HIDDEN",     8,   "DASHED"),
        ("CENTRE",     1,   "CENTER"),
        ("DIM",        4,   "Continuous"),
        ("TEXT",       7,   "Continuous"),
        ("REF",        6,   "Continuous"),   # light bar - reference only
        ("HATCH",      9,   "Continuous"),
    ]:
        lay = doc.layers.add(name)
        lay.color = color
        try:
            lay.dxf.linetype = lt
        except Exception:
            pass

    # dimension style
    ds = doc.dimstyles.get("EZDXF")
    ds.dxf.dimtxt = 2.2
    ds.dxf.dimasz = 2.0
    ds.dxf.dimexe = 1.0
    ds.dxf.dimexo = 1.0
    ds.dxf.dimgap = 0.8
    ds.dxf.dimdec = 0
    return doc


def dimstyle_override(scale):
    """DIMLFAC makes a dimension report true size on a scaled view."""
    return {"dimlfac": 1.0 / scale, "dimtxt": 2.2, "dimasz": 2.0,
            "dimdec": 0, "dimgap": 0.8}


# ------------------------------------------------------------- primitives
class View:
    """A drawing view: model mm -> sheet mm, with an origin on the sheet."""

    def __init__(self, msp, ox, oy, scale):
        self.msp, self.ox, self.oy, self.s = msp, ox, oy, scale

    def p(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def line(self, x1, y1, x2, y2, layer="OUTLINE"):
        self.msp.add_line(self.p(x1, y1), self.p(x2, y2), dxfattribs={"layer": layer})

    def rect(self, x1, y1, x2, y2, layer="OUTLINE"):
        pts = [self.p(x1, y1), self.p(x2, y1), self.p(x2, y2), self.p(x1, y2)]
        self.msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

    def circle(self, cx, cy, r, layer="OUTLINE"):
        self.msp.add_circle(self.p(cx, cy), r * self.s, dxfattribs={"layer": layer})

    def arc(self, cx, cy, r, a0, a1, layer="OUTLINE"):
        self.msp.add_arc(self.p(cx, cy), r * self.s, a0, a1, dxfattribs={"layer": layer})

    def cmark(self, cx, cy, r, layer="CENTRE"):
        e = r * 1.6
        self.line(cx - e, cy, cx + e, cy, layer)
        self.line(cx, cy - e, cx, cy + e, layer)

    # ---- dimensions ----
    def dimh(self, x1, x2, y, off, text="<>"):
        d = self.msp.add_linear_dim(
            base=self.p((x1 + x2) / 2, y + off / self.s),
            p1=self.p(x1, y), p2=self.p(x2, y),
            text=text, dxfattribs={"layer": "DIM"},
            override=dimstyle_override(self.s))
        d.render()

    def dimv(self, y1, y2, x, off, text="<>"):
        d = self.msp.add_linear_dim(
            base=self.p(x + off / self.s, (y1 + y2) / 2),
            p1=self.p(x, y1), p2=self.p(x, y2), angle=90,
            text=text, dxfattribs={"layer": "DIM"},
            override=dimstyle_override(self.s))
        d.render()

    def label(self, x, y, txt, h=2.5, layer="TEXT", align="LEFT"):
        """x, y are MODEL mm."""
        t = self.msp.add_text(txt, dxfattribs={"layer": layer, "height": h})
        t.set_placement(self.p(x, y), align=TextEntityAlignment[align])

    def slabel(self, x, dy, txt, h=2.5, layer="TEXT", align="LEFT"):
        """x in MODEL mm, dy is an offset in SHEET mm from the view origin."""
        px, _ = self.p(x, 0.0)
        t = self.msp.add_text(txt, dxfattribs={"layer": layer, "height": h})
        t.set_placement((px, self.oy + dy), align=TextEntityAlignment[align])


def sheet_text(msp, x, y, txt, h=2.5, layer="TEXT", align="LEFT", style=None):
    a = {"layer": layer, "height": h}
    if style:
        a["style"] = style
    t = msp.add_text(txt, dxfattribs=a)
    t.set_placement((x, y), align=TextEntityAlignment[align])
    return t


# ------------------------------------------------------------------ views
def front_elevation(msp, ox, oy, s):
    """Looking along +Y.  X across, Z up.  Rail, plates, clamps, bar."""
    v = View(msp, ox, oy, s)
    L2 = P["RAIL_LEN"] / 2
    v.rect(-L2, -RAIL_H, L2, 0)                              # rail
    v.line(-L2, -P["RAIL_T"], L2, -P["RAIL_T"], "HIDDEN")     # tube walls
    v.line(-L2, -RAIL_H + P["RAIL_T"], L2, -RAIL_H + P["RAIL_T"], "HIDDEN")

    for sx in (-1, 1):                                        # chassis plates
        cx = sx * P["PLATE_CTR_X"]
        v.rect(cx - P["PLATE_LEN"] / 2, -RAIL_H - P["PLATE_T"],
               cx + P["PLATE_LEN"] / 2, -RAIL_H)
        for hx in (cx - P["PLATE_PITCH"] / 2, cx + P["PLATE_PITCH"] / 2):
            v.line(hx, -RAIL_H - P["PLATE_T"], hx, 0, "CENTRE")

    for sx in (-1, 1):                                        # clamps
        cx = sx * P["CLAMP_X"]
        v.rect(cx - P["CLAMP_L"] / 2, 0, cx + P["CLAMP_L"] / 2, P["SADDLE_H"])
        v.rect(cx - P["CLAMP_L"] / 2, P["SADDLE_H"],
               cx + P["CLAMP_L"] / 2, P["SADDLE_H"] + P["STRAP_H"])

    b2 = P["BAR_LEN"] / 2                                     # light bar (ref)
    v.rect(-b2, P["SADDLE_H"] - P["BAR_D"] / 2,
           b2, P["SADDLE_H"] + P["BAR_D"] / 2, "REF")
    v.line(-L2, P["SADDLE_H"], L2, P["SADDLE_H"], "CENTRE")

    top = P["SADDLE_H"] + P["STRAP_H"]
    v.dimh(-L2, L2, -RAIL_H - P["PLATE_T"], -34)
    v.dimh(-P["PLATE_CTR_X"], P["PLATE_CTR_X"], -RAIL_H - P["PLATE_T"], -24)
    v.dimh(-P["CLAMP_X"], P["CLAMP_X"], -RAIL_H - P["PLATE_T"], -14)
    v.dimh(-b2, b2, top, 10)
    v.dimv(-RAIL_H - P["PLATE_T"], top, L2, 14)
    v.slabel(-L2, 30.0, "FRONT  ELEVATION      1 : 10", 3.2)
    return v


def plan(msp, ox, oy, s):
    """Looking down.  X across, Y up."""
    v = View(msp, ox, oy, s)
    L2, W2 = P["RAIL_LEN"] / 2, P["RAIL_W"] / 2
    v.rect(-L2, -W2, L2, W2)
    v.line(-L2, 0, L2, 0, "CENTRE")

    for sx in (-1, 1):
        cx = sx * P["PLATE_CTR_X"]
        v.rect(cx - P["PLATE_LEN"] / 2, -W2, cx + P["PLATE_LEN"] / 2, W2, "HIDDEN")
        for hx in (cx - P["PLATE_PITCH"] / 2, cx + P["PLATE_PITCH"] / 2):
            v.circle(hx, 0, P["PLATE_HOLE_D"] / 2)
            v.cmark(hx, 0, P["PLATE_HOLE_D"] / 2)
    for sx in (-1, 1):
        cx = sx * P["CLAMP_X"]
        v.rect(cx - P["CLAMP_L"] / 2, -P["CLAMP_W"] / 2,
               cx + P["CLAMP_L"] / 2, P["CLAMP_W"] / 2, "HIDDEN")
        for sy in (-1, 1):
            v.circle(cx, sy * P["CBOLT_Y"], P["CBOLT_D"] / 2)
            v.cmark(cx, sy * P["CBOLT_Y"], P["CBOLT_D"] / 2)

    v.dimv(-W2, W2, -L2, -14)
    v.dimh(P["PLATE_CTR_X"] - P["PLATE_PITCH"] / 2,
           P["PLATE_CTR_X"] + P["PLATE_PITCH"] / 2, W2, 10)
    v.slabel(-L2, -18.0, "PLAN      1 : 10", 3.2)
    return v


def section_aa(msp, ox, oy, s):
    """Cut through a clamp station, looking along +X."""
    v = View(msp, ox, oy, s)
    W2 = P["RAIL_W"] / 2
    t = P["RAIL_T"]
    # rail RHS section
    v.rect(-W2, -RAIL_H, W2, 0)
    v.rect(-W2 + t, -RAIL_H + t, W2 - t, -t)
    # saddle
    v.rect(-P["CLAMP_W"] / 2, 0, P["CLAMP_W"] / 2, P["SADDLE_H"])
    v.arc(0, P["SADDLE_H"], BORE_R, 180, 360)
    # strap
    v.rect(-P["CLAMP_W"] / 2, P["SADDLE_H"],
           P["CLAMP_W"] / 2, P["SADDLE_H"] + P["STRAP_H"])
    v.arc(0, P["SADDLE_H"], BORE_R, 0, 180)
    # bar (reference)
    v.circle(0, P["SADDLE_H"], P["BAR_D"] / 2, "REF")
    v.cmark(0, P["SADDLE_H"], P["BAR_D"] / 2)
    # clamp bolts + crush tubes
    top = P["SADDLE_H"] + P["STRAP_H"]
    for sy in (-1, 1):
        bx = sy * P["CBOLT_Y"]
        v.line(bx - P["CBOLT_D"] / 2, -RAIL_H, bx - P["CBOLT_D"] / 2, top, "HIDDEN")
        v.line(bx + P["CBOLT_D"] / 2, -RAIL_H, bx + P["CBOLT_D"] / 2, top, "HIDDEN")
        v.line(bx, -RAIL_H - 6, bx, top + 6, "CENTRE")
        v.rect(bx - P["CRUSH_OD_M6"] / 2, -RAIL_H + t,
               bx + P["CRUSH_OD_M6"] / 2, -t, "HIDDEN")

    v.dimh(-W2, W2, -RAIL_H, -12)
    v.dimh(-P["CBOLT_Y"], P["CBOLT_Y"], top, 20)
    v.dimv(-RAIL_H, 0, -W2, -14)
    v.dimv(0, P["SADDLE_H"], P["CLAMP_W"] / 2, 12)
    v.dimv(P["SADDLE_H"], top, P["CLAMP_W"] / 2, 24)
    v.slabel(-P["CLAMP_W"] / 2, 66.0, "SECTION  A-A      1 : 2", 3.2)
    v.slabel(-P["CLAMP_W"] / 2, 59.0,
             f'BORE Ø{2*BORE_R:.0f}  ({P["LINER_T"]:.0f} EPDM LINER, BAR Ø{P["BAR_D"]:.0f})', 2.2)
    return v


def detail_mount(msp, ox, oy, s):
    """Chassis mounting plate, plan + elevation."""
    v = View(msp, ox, oy, s)
    L2, W2 = P["PLATE_LEN"] / 2, P["PLATE_W"] / 2
    v.rect(-L2, -W2, L2, W2)
    for hx in (-P["PLATE_PITCH"] / 2, P["PLATE_PITCH"] / 2):
        v.circle(hx, 0, P["PLATE_HOLE_D"] / 2)
        v.cmark(hx, 0, P["PLATE_HOLE_D"] / 2)
    v.line(-L2, 0, L2, 0, "CENTRE")
    v.dimh(-L2, L2, -W2, -12)
    v.dimh(-P["PLATE_PITCH"] / 2, P["PLATE_PITCH"] / 2, W2, 10)
    v.dimv(-W2, W2, L2, 12)
    v.slabel(-L2, 38.0, "DETAIL  B  -  CHASSIS PLATE (2 OFF)      1 : 2", 3.2)
    v.slabel(-L2, -44.0,
             f'2 × Ø{P["PLATE_HOLE_D"]:.0f} THRU  (M10 CLEARANCE)   PLATE {P["PLATE_T"]:.0f} THK', 2.2)
    return v


# ------------------------------------------------------------- sheet frame
def frame_and_title(msp, meta):
    msp.add_lwpolyline([(M, M), (SW - M, M), (SW - M, SH - M), (M, SH - M)],
                       close=True, dxfattribs={"layer": "SHEET"})
    # ---- title block ----
    x0, y0, x1, y1 = 250.0, M, SW - M, 48.0
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                       close=True, dxfattribs={"layer": "TITLE"})
    for yy in (y0 + 7, y0 + 14, y0 + 21):
        msp.add_line((x0, yy), (x1, yy), dxfattribs={"layer": "TITLE"})
    msp.add_line((x0 + 98, y0), (x0 + 98, y0 + 21), dxfattribs={"layer": "TITLE"})

    sheet_text(msp, x0 + 3, y0 + 30.5, meta["title"], 4.4, "TITLE")
    sheet_text(msp, x0 + 3, y0 + 24.0, meta["subtitle"], 2.2, "TEXT")
    sheet_text(msp, x0 + 3, y0 + 16.3, f'DRAWN     {meta["drawn"]}', 2.3)
    sheet_text(msp, x0 + 3, y0 + 9.3, f'DATE       {meta["date"]}', 2.3)
    sheet_text(msp, x0 + 3, y0 + 2.3, f'MATERIAL  {meta["material"]}', 2.3)
    sheet_text(msp, x0 + 101, y0 + 16.3, f'SCALE   {meta["scale"]}', 2.3)
    sheet_text(msp, x0 + 101, y0 + 9.3, "SIZE     A3", 2.3)
    sheet_text(msp, x0 + 101, y0 + 2.3, f'DWG    {meta["number"]}  REV {meta["rev"]}', 2.3)

    # ---- bill of materials ----
    bx0, by1 = 250.0, 155.0
    rows = meta["bom"]
    rh = 7.0
    by0 = by1 - rh * (len(rows) + 1)
    msp.add_lwpolyline([(bx0, by0), (SW - M, by0), (SW - M, by1), (bx0, by1)],
                       close=True, dxfattribs={"layer": "TITLE"})
    cols = [bx0, bx0 + 14, bx0 + 100, bx0 + 122, SW - M]
    for cx in cols[1:-1]:
        msp.add_line((cx, by0), (cx, by1), dxfattribs={"layer": "TITLE"})
    for i in range(len(rows) + 1):
        yy = by1 - rh * i
        msp.add_line((bx0, yy), (SW - M, yy), dxfattribs={"layer": "TITLE"})
    hdr = ["No", "DESCRIPTION", "QTY", "MATERIAL"]
    for c, h in zip(cols, hdr):
        sheet_text(msp, c + 2, by1 - rh + 2.2, h, 2.3, "TITLE")
    for i, r in enumerate(rows, start=1):
        yy = by1 - rh * (i + 1) + 2.2
        for c, val in zip(cols, r):
            sheet_text(msp, c + 2, yy, str(val), 2.2)
    sheet_text(msp, bx0, by1 + 3, "BILL OF MATERIALS", 2.8, "TITLE")

    # ---- notes ----
    nx, ny = M + 5, 68.0
    sheet_text(msp, nx, ny, "NOTES", 3.0, "TITLE")
    for i, n in enumerate(meta["notes"]):
        sheet_text(msp, nx, ny - 5.6 * (i + 1), n, 2.2)


# ------------------------------------------------------------------- main
def build(path, layout_name=None):
    """Draw the sheet.

    By default it goes in model space, 1:1 in millimetres -- that is the
    standalone A3 DXF.  Pass ``layout_name`` and it is drawn into a paper
    space layout of that name instead, on a real A3 page, leaving model
    space empty.  That file is the seed the AutoCAD builder opens, so the
    finished DWG carries the 3D assembly in model space and this sheet on
    its own layout.  Every view routine takes the layout as its first
    argument, so nothing else has to change.
    """
    doc = new_doc()
    if layout_name:
        msp = doc.layouts.new(layout_name)
        msp.page_setup(size=(SW, SH), margins=(0, 0, 0, 0), units="mm",
                       name="A3")
        msp.dxf.taborder = 1
        for spare in ("Layout1", "Layout2"):
            if spare in doc.layouts.names():
                doc.layouts.delete(spare)
    else:
        msp = doc.modelspace()

    front_elevation(msp, 120.0, 252.0, 0.10)
    plan(msp, 120.0, 195.0, 0.10)
    section_aa(msp, 330.0, 200.0, 0.50)
    detail_mount(msp, 112.0, 128.0, 0.50)

    frame_and_title(msp, dict(
        title="FRONT LED LIGHT-BAR HOLDER",
        subtitle="ELECTRIC ROVER  -  FRONT LIGHTING MOUNT ASSEMBLY",
        drawn="K. FATKHUTDINOV",
        date="2026-09-04",
        material="6061-T6 ALUMINIUM (SEE BOM)",
        scale="AS SHOWN",
        number="FLM-001",
        rev="A",
        bom=[
            (1, "RAIL, RHS 90 x 30 x 3, 2000 LG", 1, "6061-T6"),
            (2, "CHASSIS MOUNTING PLATE 200x90x10", 2, "6061-T6"),
            (3, "CLAMP SADDLE 80x90x45", 2, "6061-T6"),
            (4, "CLAMP STRAP 80x90x22", 2, "6061-T6"),
            (5, "CRUSH TUBE 20 OD x 11 ID x 24", 4, "304 STAINLESS"),
            (6, "CRUSH TUBE 14 OD x 6.6 ID x 24", 4, "304 STAINLESS"),
            (7, "BOLT M10 x 60, NUT + WASHERS", 4, "A2-70"),
            (8, "BOLT M6 x 100, NYLOC + WASHERS", 4, "A2-70"),
            (9, "EPDM LINER 2 THK x 170 x 80", 2, "EPDM 60 SH"),
            (10, "LED LIGHT BAR Ø50 x 900 (REF)", 1, "PURCHASED"),
        ],
        notes=[
            "1.  ALL DIMENSIONS IN MILLIMETRES.  DO NOT SCALE FROM DRAWING.",
            "2.  GENERAL TOLERANCE ISO 2768-m.  HOLE POSITIONS ±0.5.",
            "3.  BREAK ALL SHARP EDGES 0.5 x 45°.",
            "4.  RAIL SECTION IS A CLOSED RHS.  FIT CRUSH TUBES AT EVERY",
            "     BOLT BEFORE TIGHTENING - THE WALLS WILL COLLAPSE WITHOUT THEM.",
            "5.  ITEM 9 EPDM LINER TO BE FITTED BETWEEN BAR AND CLAMP BORE.",
            "6.  TORQUE:  M10 = 40 Nm,  M6 = 9 Nm.  USE THREADLOCKER.",
            "7.  ANODISE ALL ALUMINIUM PARTS AFTER MACHINING (CLEAR, 15 µm).",
            "8.  MASS OF FABRICATED ASSEMBLY = 6.54 kg (EXCL. BAR & FASTENERS).",
        ],
    ))

    doc.saveas(path)
    print(f"wrote {path}")
    return doc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="../cad/front-led-mount-drawing.dxf")
    ap.add_argument("--layout", metavar="NAME", default=None,
                    help="draw the sheet on a paper space layout of this name "
                         "instead of in model space (used to seed the DWG)")
    a = ap.parse_args()
    build(a.out, a.layout)

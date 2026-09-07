# Front LED Light-Bar Holder — Electric Rover

A bracket that carries a Ø50 × 900 mm LED light bar across the front of an
electric rover: a 2 m rail bolted to two chassis pick-up points, with two
split clamps holding the light bar 45 mm above it.

![Assembly](docs/assembly-iso.png)

Completed from an unfinished AutoCAD model (`front LED.dwg`, AutoCAD 2018
format, last saved 16 Mar 2026). The original contained seven loose solids
and three construction lines, none of them assembled, dimensioned, or
positioned relative to one another.

---

## The completed design

Origin is the centre of the rail, on its top face. **+X** along the rail,
**+Y** forward (the way the light points), **+Z** up.

| Item | Description | Qty | Material |
|---|---|---|---|
| 1 | Rail, RHS 90 × 30 × 3, 2000 long | 1 | 6061-T6 |
| 2 | Chassis mounting plate 200 × 90 × 10, 2 × Ø11 @ 120 | 2 | 6061-T6 |
| 3 | Clamp saddle 80 × 90 × 45, Ø54 bore | 2 | 6061-T6 |
| 4 | Clamp strap 80 × 90 × 22, Ø54 bore | 2 | 6061-T6 |
| 5 | Crush tube 20 OD × 11 ID × 24 | 4 | 304 stainless |
| 6 | Crush tube 14 OD × 6.6 ID × 24 | 4 | 304 stainless |
| 7 | Bolt M10 × 60, nut + washers | 4 | A2-70 |
| 8 | Bolt M6 × 100, nyloc + washers | 4 | A2-70 |
| 9 | EPDM liner 2 thk × 170 × 80 | 2 | EPDM 60 Sh |
| 10 | LED light bar Ø50 × 900 *(reference)* | 1 | purchased |

Envelope **2000 × 90 × 110 mm**, fabricated mass **6.54 kg** (6.28 kg aluminium
+ 0.26 kg stainless), light bar and fasteners excluded.

![Clamp exploded](docs/clamp-exploded.png)

![Chassis mount exploded](docs/mount-exploded.png)

### Three decisions worth explaining

**1. The rail section was changed from flat bar to RHS.** This is the one place
the completed model departs from what was drawn, and it is the reason the
project needed finishing rather than just assembling. Running the beam case —
simply supported at the two chassis plates 1700 mm apart, two clamp loads
550 mm inboard of each support, plus self weight:

| Section | I (mm⁴) | Mass | Deflection | L/δ | σ | f₁ |
|---|---|---|---|---|---|---|
| Flat 90 × 8 *(as drawn)* | 3 840 | 3.89 kg | **15.74 mm** | L/108 | 14.2 MPa | **5.0 Hz** |
| Flat 90 × 10 | 7 500 | 4.86 kg | 9.06 mm | L/188 | 10.2 MPa | 6.4 Hz |
| **RHS 90 × 30 × 3** | **105 732** | **3.69 kg** | **0.56 mm** | L/3050 | 1.9 MPa | **26.4 Hz** |
| RHS 90 × 40 × 3 | 204 872 | 4.02 kg | 0.30 mm | L/5669 | 1.4 MPa | 35.8 Hz |

Stress is never the constraint — everything is far below the 240 MPa yield of
6061-T6. The rail is **stiffness driven**. The flat bar as drawn sags about
16 mm at the clamps, which visibly mis-aims a light bar, and its first bending
mode lands at ~5 Hz — squarely inside the band a rover chassis excites over
rough ground. The 90 × 30 × 3 RHS is 28× stiffer, moves the first mode to
26 Hz, and is *lighter* than the flat bar it replaces.

If you want the original flat bar anyway, set `*RAIL-SECTION*` to `"FLAT"` in
the LISP (and `RAIL_SECTION` in `params.py`) and everything regenerates.

**2. Crush tubes at every bolt.** A closed RHS collapses when you torque a bolt
through both walls. Eight stainless sleeves sit in the cavity so the preload
goes through the sleeve, not the tube wall. Without them, item 1 gets dented
flat at all eight bolt positions on first assembly.

**3. Ø54 bore for a Ø50 bar.** The original clamp bore matched the bar exactly,
which leaves no room for the 2 mm EPDM liner. The liner both grips the bar and
keeps aluminium off the light-bar housing, so the rail's 26 Hz mode doesn't
fret it.

---

## Files

```
front-led-mount/
├── cad/
│   ├── front-LED_ORIGINAL.dwg          untouched original, for reference
│   ├── front-LED_ORIGINAL-decoded.dxf  the original decoded to DXF (LibreDWG)
│   ├── front-led-mount-3D.dwg          3D assembly + A3 layout  <-- the CAD file
│   ├── front-led-mount-sheet-A3.dxf    the sheet on a paper space layout (build seed)
│   └── front-led-mount-drawing.dxf     the same sheet in model space, standalone
├── scripts/
│   ├── front_led_mount.lsp             parametric 3D model builder for AutoCAD
│   ├── build_in_autocad.sh             runs that builder headlessly inside AutoCAD
│   ├── params.py                       single source of truth for all dimensions
│   ├── make_drawing.py                 generates the A3 DXF above
│   ├── verify_model.py                 independent solid + interference + beam check
│   ├── render_views.py                 shaded views for this README
│   └── dxf_to_png.py                   DXF preview renderer
├── exports/stl/                        16 STL files, one per part
└── docs/                               images
```

## Using it

### The 3D model

It is already built — open it:

```bash
open -a "AutoCAD 2026" /Users/karimfatkhutdinov/uofm/Portfolio/front-led-mount/cad/front-led-mount-3D.dwg
```

One file, both halves of the job:

| | |
|---|---|
| **Model** | the assembly — 32 ACIS solids on seven named layers, in millimetres |
| **A3 DRAWING** | the manufacturing sheet, on a 420 × 297 mm page, ready to plot |

It was produced by AutoCAD itself, not written by an exporter — see
*Built in AutoCAD* below.

### Rebuilding it

Headlessly, straight from the shell — this is how the file in `cad/` was made:

```bash
./scripts/build_in_autocad.sh
```

Or interactively, in a **new** drawing (`acadiso.dwt`, millimetres):

1. `APPLOAD` → select `scripts/front_led_mount.lsp` → **Load**
2. `FLM` — builds the whole assembly on named layers
3. `FLMVIEWS` — SW isometric, shaded
4. `FLMINFO` — prints volume and mass per layer

Every dimension lives in one parameter block at the top of the file. Change a
number, re-run `FLM`, and the assembly regenerates.

### The manufacturing drawing

An A3 sheet drawn 1:1 in millimetres — front elevation and plan at 1:10,
section A-A through a clamp and the chassis plate detail at 1:2, with a title
block, BOM and notes. Dimensions carry a `DIMLFAC` override, so every one
reads the true size of the part despite the view scale.

It exists twice, from the same code:

- **on the `A3 DRAWING` layout of `front-led-mount-3D.dwg`** — the one to
  plot. `make_drawing.py --layout` writes it into paper space with the A3 page
  already set up, and `build_in_autocad.sh` opens that as its seed, so the
  finished DWG carries the sheet and the model together.
- **`cad/front-led-mount-drawing.dxf`** — the same sheet in model space as a
  standalone file, for importing into someone else's drawing or handing to a
  shop that does not want the 3D model.

![Drawing sheet](docs/drawing-sheet.png)

### Re-generating everything

```bash
cd scripts
python3 make_drawing.py --layout "A3 DRAWING" -o ../cad/front-led-mount-sheet-A3.dxf
./build_in_autocad.sh   -o ../cad/front-led-mount-3D.dwg
python3 verify_model.py --stl ../exports/stl
python3 make_drawing.py -o ../cad/front-led-mount-drawing.dxf
python3 render_views.py -o ../docs
```

Order matters for the first two: the builder seeds the DWG from the sheet, so
regenerate the sheet before rebuilding the model.

Needs `ezdxf`, `trimesh`, `manifold3d`, `numpy`, `scipy`, `matplotlib`.

---

## Verification

`verify_model.py` rebuilds the same solids with an independent CSG kernel
(trimesh + manifold3d) and checks them:

```
part       qty   volume cm3   mass kg   watertight
rail         1       1364.9     3.685   True
plate        2        356.2     0.962   True
saddle       2        458.8     1.239   True
strap        2        147.7     0.399   True
crush        8         32.5     0.255   True
bar          1       1765.9     4.768   True

INTERFERENCE CHECK
0 interfering pairs  ->  PASS
envelope  2000 x 90 x 110 mm
```

All ten solids are closed and watertight, and no two parts occupy the same
space.

That is a check on the geometry the LISP *describes*. AutoCAD has since been
asked the same question about the solids it actually built, with `MASSPROP`:

| part | qty | trimesh cm³ | **AutoCAD cm³** | Δ |
|---|---|---|---|---|
| rail | 1 | 1364.9 | **1364.898** | exact |
| plate | 2 | 356.2 | **356.199** | exact |
| saddle + strap | 4 | 606.5 | **606.228** | 0.04 % |
| crush tube | 8 | 32.5 | **32.531** | exact |
| light bar *(ref)* | 1 | 1765.9 | **1767.146** | 0.07 % |

The two differences are the tessellation error in the *Python* check, not in
the model: trimesh facets a cylinder into flat triangles and so slightly
under-reads anything with a curved face, while ACIS integrates the real
surface. `1767.146 cm³` is exactly π/4 × 50² × 900.

Every solid was also measured against `params.py` for position: all 32 land on
their nominal centres to 10⁻⁶ mm, and the drawing extents are
X ±1000, Y ±45, Z −52 → +78 (the fabricated envelope, excluding fastener heads,
is the documented 2000 × 90 × 110).

---

## Built in AutoCAD

`FLM` has been run inside AutoCAD 2026 and `cad/front-led-mount-3D.dwg` is
what it produced — real ACIS solids from real `BOX` / `CYLINDER` / `SUBTRACT`
commands, saved by AutoCAD in 2018 DWG format.

The GUI on this machine still can't be driven (the terminal has neither Screen
Recording nor Apple Events permission), but it doesn't need to be: AutoCAD for
Mac ships its headless core engine inside the application bundle, at
`AutoCAD 2026.app/Contents/Helpers/AcCoreConsole.app`. It loads AutoLISP and
runs the same command stack as the GUI with no window at all.
`scripts/build_in_autocad.sh` wraps it, seeding the drawing from
`cad/front-led-mount-sheet-A3.dxf` so that the sheet is already on its layout
before the first solid is drawn:

```
AutoCAD engine : AcCoreConsole 25.1.119.325
seed drawing   : acadiso3D.dwt
output         : cad/front-led-mount-3D.dwg

Building rail ...
Building chassis plates ...
Building clamps ...
Building crush tubes ...
Placing fasteners and light bar ...

  LAYER              QTY      VOLUME (cm3)     MASS (kg)
  -----------------------------------------------------------------
  FLM-LED-REF        1        1767.1          4.771
  FLM-FASTENER       16        43.7          0.118
  FLM-CRUSH          8        32.5          0.255
  FLM-CLAMP          4        606.2          1.637
  FLM-PLATE          2        356.2          0.962
  FLM-RAIL           1        1364.9          3.685
  Fabricated mass (excl. bar + fasteners): 6.539 kg
```

which is the 6.54 kg in the BOM at the top of this page, arrived at
independently.

### What the first real run broke

The builder had never actually been executed before, and running it found
three genuine faults — all now fixed in `front_led_mount.lsp`:

**1. `3DOSMODE`, not `OSMODE`.** This was the serious one. The script cleared
`OSMODE`, which only covers *2D* object snap. `acadiso3D.dwt` ships with
`3DOSMODE = 174` — vertex, midpoint-on-edge, centre-of-face and friends — and
`OSNAPCOORD` defaults to `2`, which means *typed coordinates do not override a
running snap when the input comes from a script*. So every point after the
first solid was silently pulled onto the nearest feature of whatever was
already drawn. Boxes landed on the wrong faces, bores missed their bosses, and
one clamp bore had its axis endpoint snapped onto its own base point, which
AutoCAD reported as the wonderfully unhelpful `Value must be nonzero.` The
rail came out at 3382 cm³ instead of 1365 — 2.5× too heavy, from a script that
raised no error. `FLM` now clears `3DOSMODE` and sets `OSNAPCOORD` to 1, and
restores both afterwards.

This one matters in the GUI too: anyone running `FLM` from `acadiso3D.dwt`
with 3D snaps on would have got the same wrong model.

**2. No ActiveX in the console.** `vl-load-com` throws there, and an error
during `load` aborts the whole file, so nothing defined after it ever existed.
It is now wrapped in `vl-catch-all-apply`, and `FLMINFO` picks its volume
route at run time: ActiveX in the full application, `MASSPROP` written to an
`.mpr` report and parsed back when ActiveX is missing.

**3. `FLMINFO` costed the stainless crush tubes as aluminium**, and so
under-reported the assembly by 0.17 kg. It now uses 7.85 g/cm³ for
`FLM-CRUSH`, which is what makes the table above agree with the BOM.

### Still untested

The interactive path — `APPLOAD` then `FLM` at the AutoCAD command line — has
not been exercised, only the identical LISP running in the core engine. The
one thing to watch there is `SECURELOAD`: the batch script sets it to 0, but
`APPLOAD` from the GUI may still refuse an untrusted folder. Add `scripts/`
under **Preferences → Application → Security → Trusted Locations** if it does.

---

## Next steps

- Set `RAIL_LEN` and `PLATE_CTR_X` to the rover's real front width and chassis
  pick-up spacing — these are the two numbers taken from the original drawing's
  extents rather than from the vehicle.
- Confirm the light bar's actual mass; 2.5 kg is assumed. The deflection and
  frequency results scale roughly with √mass.
- The 26 Hz first mode is a hand calculation on a uniform beam. If the rover
  sees sustained excitation above ~15 Hz, run a proper modal analysis with the
  clamp and bar masses placed discretely.
- Add a slotted adjustment in the saddle if the light bar needs aiming
  adjustment after mounting; presently the aim is fixed by the bore axis.

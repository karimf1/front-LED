"""
params.py -- single source of truth for the front LED light-bar holder.

These values are mirrored in front_led_mount.lsp (the AutoCAD builder).
If you change a number here, change it there too -- or regenerate the
LISP parameter block with:  python3 sync_params.py

All dimensions in millimetres.  Origin is the centre of the rail, on its
top face:  +X along the rail, +Y forward (the way the light points), +Z up.
"""

P = dict(
    # ---- main rail -----------------------------------------------------
    RAIL_LEN=2000.0,      # overall length
    RAIL_W=90.0,          # width  (Y)
    RAIL_H=30.0,          # depth  (Z)
    RAIL_T=3.0,           # wall thickness
    RAIL_SECTION="TUBE",  # "TUBE" = 90x30x3 RHS (recommended)
                          # "FLAT" = solid flat bar, as originally drawn
    RAIL_FLAT_T=8.0,

    # ---- chassis mounting plates ---------------------------------------
    PLATE_LEN=200.0,
    PLATE_W=90.0,
    PLATE_T=10.0,
    PLATE_CTR_X=850.0,    # +/- from origin  -> 1700 mount span
    PLATE_PITCH=120.0,    # hole centres
    PLATE_HOLE_D=11.0,    # M10 clearance

    # ---- LED light bar (reference, purchased part) ----------------------
    BAR_D=50.0,
    BAR_LEN=900.0,
    LINER_T=2.0,          # EPDM isolation liner -> bore = BAR_D + 2*LINER_T

    # ---- clamp (saddle + strap) -----------------------------------------
    CLAMP_X=300.0,        # +/- from origin -> 600 clamp span
    CLAMP_L=80.0,
    CLAMP_W=90.0,
    SADDLE_H=45.0,        # rail top face -> bar axis
    STRAP_H=22.0,
    CBOLT_D=6.6,          # M6 clearance
    CBOLT_Y=31.0,         # +/- from rail centreline

    # ---- crush tubes -----------------------------------------------------
    CRUSH_OD_M10=20.0,
    CRUSH_OD_M6=14.0,

    # ---- materials --------------------------------------------------------
    DENS=2.70e-3,         # 6061-T6 aluminium, g/mm^3
    DENS_STEEL=7.85e-3,   # 304 stainless, g/mm^3
    E_AL=69000.0,         # Young's modulus, N/mm^2
    SY_AL=240.0,          # 6061-T6 yield, N/mm^2

    # ---- load case ---------------------------------------------------------
    BAR_MASS=2.5,         # kg, the light bar being carried
)

# derived
BORE_R = P["BAR_D"] / 2 + P["LINER_T"]
RAIL_H_EFF = P["RAIL_H"] if P["RAIL_SECTION"] == "TUBE" else P["RAIL_FLAT_T"]
MOUNT_SPAN = 2 * P["PLATE_CTR_X"]
CLAMP_SPAN = 2 * P["CLAMP_X"]

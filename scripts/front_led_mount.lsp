;;; ===================================================================
;;;  front_led_mount.lsp
;;;  Front LED light-bar holder for an electric rover
;;;  Parametric 3D solid model builder for AutoCAD (2018+ / AutoCAD 2026)
;;;
;;;  USAGE
;;;    1.  Start a NEW drawing (acadiso.dwt, millimetres).
;;;    2.  APPLOAD  ->  select this file  ->  Load.
;;;    3.  Type:  FLM        builds the complete assembly
;;;               FLMVIEWS   sets a SW isometric + shaded view
;;;               FLMINFO    prints mass / volume of every part
;;;
;;;  COORDINATE SYSTEM (WCS, millimetres)
;;;    origin  = centre of the rail, on its TOP face
;;;    +X      = along the rail (vehicle left -> right)
;;;    +Y      = forward (direction the light points)
;;;    +Z      = up
;;;
;;;  All dimensions are driven by the parameter block below - change a
;;;  number there and re-run FLM to regenerate the whole assembly.
;;; ===================================================================

;; ActiveX is present in the full AutoCAD application but NOT in
;; AcCoreConsole, the headless engine used to build this model in batch --
;; there vl-load-com throws and would abort the load.  Guard it, and let
;; flm:has-vla decide which volume route to take later on.
(vl-catch-all-apply 'vl-load-com '())

(defun flm:has-vla ()
  (if (member 'VLAX-ENAME->VLA-OBJECT (atoms-family 0)) T nil)
)

;;; -------------------------------------------------------------------
;;;  PARAMETERS   <-- edit these to suit the vehicle
;;; -------------------------------------------------------------------
(defun flm:params ()
  (setq
    ;; ---- main rail -------------------------------------------------
    *RAIL-LEN*     2000.0   ; overall length
    *RAIL-W*         90.0   ; width  (Y)
    *RAIL-H*         30.0   ; depth  (Z)
    *RAIL-T*          3.0   ; wall thickness (tube section only)
    *RAIL-SECTION*  "TUBE"  ; "TUBE" = 90x30x3 RHS  (recommended)
                            ; "FLAT" = solid flat bar, as originally drawn
    *RAIL-FLAT-T*     8.0   ; thickness used when *RAIL-SECTION* = "FLAT"

    ;; ---- chassis mounting plates ----------------------------------
    *PLATE-LEN*     200.0   ; along X
    *PLATE-W*        90.0   ; along Y
    *PLATE-T*        10.0   ; thickness
    *PLATE-CTR-X*   850.0   ; +/- distance of plate centre from origin
    *PLATE-PITCH*   120.0   ; hole centres, along X
    *PLATE-HOLE-D*   11.0   ; M10 clearance

    ;; ---- LED light bar (reference geometry, not a made part) -------
    *BAR-D*          50.0   ; light-bar outside diameter
    *BAR-LEN*       900.0   ; light-bar length
    *LINER-T*         2.0   ; EPDM isolation liner wrapped round the bar.
                            ;   The clamp bore is BAR-D + 2*LINER-T, so the
                            ;   bar never touches bare aluminium - this is
                            ;   what stops the rail's 26 Hz mode fretting
                            ;   the light-bar housing.

    ;; ---- clamp (saddle + strap) ------------------------------------
    *CLAMP-X*       300.0   ; +/- distance of clamp centre from origin
    *CLAMP-L*        80.0   ; along X
    *CLAMP-W*        90.0   ; along Y
    *SADDLE-H*       45.0   ; saddle height above rail top face
                            ;   ( = height of the bar axis )
    *STRAP-H*        22.0   ; strap thickness above the bar axis
    *CBOLT-D*         6.6   ; M6 clearance
    *CBOLT-Y*        31.0   ; +/- bolt centre from the rail centreline

    ;; ---- crush tubes (stop the RHS being crushed by bolt preload) --
    *CRUSH-OD-M10*   20.0
    *CRUSH-OD-M6*    14.0

    ;; ---- misc --------------------------------------------------------
    *MAT-DENSITY*   2.70e-3 ; 6061-T6 aluminium, g/mm^3
    *MAT-DENSITY-S* 7.85e-3 ; 304 stainless, g/mm^3 - the crush tubes only
  )
  (princ)
)

;;; -------------------------------------------------------------------
;;;  LOW-LEVEL HELPERS
;;; -------------------------------------------------------------------
(defun flm:layer (name col)
  (command "_.-LAYER" "_M" name "_C" col name "")
  name
)

(defun flm:clayer (name) (setvar "CLAYER" name))

;; solid box, given its CENTRE and its X/Y/Z sizes
(defun flm:box (cx cy cz lx ly lz)
  (command "_.BOX" "_C" (list cx cy cz) "_L" lx ly lz)
  (entlast)
)

;; cylinder with its axis along Z, from z0, signed height h
(defun flm:cylz (cx cy z0 r h)
  (command "_.CYLINDER" (list cx cy z0) r h)
  (entlast)
)

;; cylinder with its axis along X, from x0 to x1
(defun flm:cylx (x0 x1 cy cz r)
  (command "_.CYLINDER" (list x0 cy cz) r "_A" (list x1 cy cz))
  (entlast)
)

;; subtract a list of tool solids from base; returns base
(defun flm:sub (base tools / ss)
  (setq ss (ssadd))
  (foreach e tools (if e (ssadd e ss)))
  (if (> (sslength ss) 0) (command "_.SUBTRACT" base "" ss ""))
  base
)

;; union a list of solids; returns the surviving solid
(defun flm:uni (lst / ss)
  (setq ss (ssadd))
  (foreach e lst (if e (ssadd e ss)))
  (if (> (sslength ss) 1) (command "_.UNION" ss ""))
  (entlast)
)

;; Volume of every solid in a selection set, summed.
;;   full AutoCAD   -> ActiveX, one property read per solid
;;   AcCoreConsole  -> MASSPROP, which is the only route without ActiveX;
;;                     it writes an .mpr report that is parsed back here.
(defun flm:volume-ss (ss / i tot)
  (if (flm:has-vla)
    (progn
      (setq i 0 tot 0.0)
      (while (< i (sslength ss))
        (setq tot (+ tot (vlax-get (vlax-ename->vla-object (ssname ss i)) 'Volume))
              i   (1+ i)))
      tot)
    (flm:volume-mpr ss)
  )
)

(defun flm:volume-mpr (ss / fn rpt fd f l v)
  (setq fn  (strcat (getvar "TEMPPREFIX") "flm-mp")
        rpt (strcat fn ".mpr")
        fd  (getvar "FILEDIA"))
  (vl-file-delete rpt)
  (setvar "FILEDIA" 0)
  (command "_.MASSPROP" ss "" "_Y" fn)
  (setvar "FILEDIA" fd)
  (setq f (open rpt "r"))
  (if f
    (progn
      (while (and (null v) (setq l (read-line f)))
        (if (wcmatch (strcase l) "*VOLUME:*")
            (setq v (atof (substr l (+ 2 (vl-string-search ":" l)))))))
      (close f)
      (vl-file-delete rpt)))
  (if v v 0.0)
)

;; the crush tubes are the one bought-in steel item on a fabricated
;; aluminium assembly, so they must not be costed at aluminium density
(defun flm:density (lay)
  (if (= lay "FLM-CRUSH") *MAT-DENSITY-S* *MAT-DENSITY*)
)

(defun flm:volume (e / ss)
  (setq ss (ssadd))
  (ssadd e ss)
  (flm:volume-ss ss)
)

;;; -------------------------------------------------------------------
;;;  PART BUILDERS
;;;  Every part is left as a SEPARATE solid - they are separate
;;;  manufactured components, so they are never unioned together.
;;; -------------------------------------------------------------------

;; ---- 1. main rail --------------------------------------------------
(defun flm:make-rail ( / h body tools sx x)
  (flm:clayer "FLM-RAIL")
  (setq h (if (= *RAIL-SECTION* "TUBE") *RAIL-H* *RAIL-FLAT-T*))
  ;; body: top face on Z = 0, so the centre sits at -h/2
  (setq body (flm:box 0.0 0.0 (- 0.0 (/ h 2.0)) *RAIL-LEN* *RAIL-W* h))
  (setq tools '())
  ;; hollow it out if it is a tube
  (if (= *RAIL-SECTION* "TUBE")
    (setq tools (cons (flm:box 0.0 0.0 (- 0.0 (/ h 2.0))
                               (+ *RAIL-LEN* 40.0)
                               (- *RAIL-W* (* 2.0 *RAIL-T*))
                               (- h (* 2.0 *RAIL-T*)))
                      tools)))
  ;; bolt holes -- drilled through both walls
  (foreach sx (list -1.0 1.0)
    ;; chassis-plate bolts (M10), on the rail centreline
    (foreach x (list (- *PLATE-CTR-X* (/ *PLATE-PITCH* 2.0))
                     (+ *PLATE-CTR-X* (/ *PLATE-PITCH* 2.0)))
      (setq tools (cons (flm:cylz (* sx x) 0.0 20.0
                                  (/ *PLATE-HOLE-D* 2.0) (- 0.0 h 60.0))
                        tools)))
    ;; clamp bolts (M6), either side of the bar bore
    (foreach y (list (- 0.0 *CBOLT-Y*) *CBOLT-Y*)
      (setq tools (cons (flm:cylz (* sx *CLAMP-X*) y 20.0
                                  (/ *CBOLT-D* 2.0) (- 0.0 h 60.0))
                        tools)))
  )
  (flm:sub body tools)
)

;; ---- 2. chassis mounting plate (x2) --------------------------------
(defun flm:make-plate (sx / cx zc body tools x)
  (flm:clayer "FLM-PLATE")
  (setq cx (* sx *PLATE-CTR-X*)
        zc (- 0.0 (flm:rail-h) (/ *PLATE-T* 2.0)))
  (setq body (flm:box cx 0.0 zc *PLATE-LEN* *PLATE-W* *PLATE-T*))
  (setq tools '())
  (foreach x (list (- cx (/ *PLATE-PITCH* 2.0)) (+ cx (/ *PLATE-PITCH* 2.0)))
    (setq tools (cons (flm:cylz x 0.0 (+ zc 20.0)
                                (/ *PLATE-HOLE-D* 2.0) -60.0)
                      tools)))
  (flm:sub body tools)
)

(defun flm:rail-h ()
  (if (= *RAIL-SECTION* "TUBE") *RAIL-H* *RAIL-FLAT-T*)
)

;; clamp bore radius = bar radius + liner thickness
(defun flm:bore-r ()
  (+ (/ *BAR-D* 2.0) *LINER-T*)
)

;; ---- 3. clamp saddle, lower half (x2) ------------------------------
(defun flm:make-saddle (sx / cx body tools y)
  (flm:clayer "FLM-CLAMP")
  (setq cx (* sx *CLAMP-X*))
  ;; block sits on the rail top face, Z = 0 .. *SADDLE-H*
  (setq body (flm:box cx 0.0 (/ *SADDLE-H* 2.0) *CLAMP-L* *CLAMP-W* *SADDLE-H*))
  ;; the bar bore -- axis at Z = *SADDLE-H*, so the top half is open
  (setq tools (list (flm:cylx (- cx *CLAMP-L*) (+ cx *CLAMP-L*)
                              0.0 *SADDLE-H* (flm:bore-r))))
  (foreach y (list (- 0.0 *CBOLT-Y*) *CBOLT-Y*)
    (setq tools (cons (flm:cylz cx y (+ *SADDLE-H* 10.0)
                                (/ *CBOLT-D* 2.0) (- 0.0 *SADDLE-H* 20.0))
                      tools)))
  (flm:sub body tools)
)

;; ---- 4. clamp strap, upper half (x2) -------------------------------
(defun flm:make-strap (sx / cx body tools y)
  (flm:clayer "FLM-CLAMP")
  (setq cx (* sx *CLAMP-X*))
  (setq body (flm:box cx 0.0 (+ *SADDLE-H* (/ *STRAP-H* 2.0))
                      *CLAMP-L* *CLAMP-W* *STRAP-H*))
  (setq tools (list (flm:cylx (- cx *CLAMP-L*) (+ cx *CLAMP-L*)
                              0.0 *SADDLE-H* (flm:bore-r))))
  (foreach y (list (- 0.0 *CBOLT-Y*) *CBOLT-Y*)
    (setq tools (cons (flm:cylz cx y (+ *SADDLE-H* *STRAP-H* 10.0)
                                (/ *CBOLT-D* 2.0) (- 0.0 *STRAP-H* 20.0))
                      tools)))
  (flm:sub body tools)
)

;; ---- 5. crush tube (one per bolt, inside the RHS) ------------------
(defun flm:make-crush (cx cy od id / z0 hh body)
  (if (= *RAIL-SECTION* "TUBE")
    (progn
      (flm:clayer "FLM-CRUSH")
      (setq z0 (- 0.0 *RAIL-T*)                     ; under the top wall
            hh (- 0.0 (- *RAIL-H* (* 2.0 *RAIL-T*))))
      (setq body (flm:cylz cx cy z0 (/ od 2.0) hh))
      (flm:sub body (list (flm:cylz cx cy (+ z0 5.0) (/ id 2.0) (- hh 10.0))))
    )
  )
)

;; ---- 6. LED light bar (reference only) -----------------------------
(defun flm:make-bar ()
  (flm:clayer "FLM-LED-REF")
  (flm:cylx (- 0.0 (/ *BAR-LEN* 2.0)) (/ *BAR-LEN* 2.0)
            0.0 *SADDLE-H* (/ *BAR-D* 2.0))
)

;; ---- 7. fasteners (reference only) ---------------------------------
(defun flm:make-bolt (cx cy ztop zbot d dhead)
  (flm:clayer "FLM-FASTENER")
  (flm:cylz cx cy ztop (/ d 2.0) (- zbot ztop))          ; shank
  (flm:cylz cx cy ztop (/ dhead 2.0) (* 0.7 dhead))      ; head
)

;;; -------------------------------------------------------------------
;;;  MAIN COMMAND
;;; -------------------------------------------------------------------
(defun C:FLM ( / oe oo o3 oc os ob sx x y h)
  (flm:params)
  (setq oe (getvar "CMDECHO")  oo (getvar "OSMODE")
        o3 (getvar "3DOSMODE") oc (getvar "OSNAPCOORD")
        os (getvar "SOLIDHIST") ob (getvar "BLIPMODE"))
  (setvar "CMDECHO" 0) (setvar "OSMODE" 0)
  ;; 3DOSMODE is the one that matters here and OSMODE does NOT cover it.
  ;; acadiso3D.dwt ships with 3DOSMODE = 174 (vertex / midpoint-on-edge /
  ;; centre-of-face ...), and OSNAPCOORD defaults to 2, which means typed
  ;; coordinates do NOT override a running snap *when the input comes from
  ;; a script*.  Leave them alone and every point after the first solid
  ;; gets pulled onto the nearest vertex or face centre of what is already
  ;; drawn: boxes land on the wrong faces, bores miss, and a bore axis can
  ;; collapse to zero length ("Value must be nonzero.").  Clear both.
  (setvar "3DOSMODE" 0) (setvar "OSNAPCOORD" 1)
  (setvar "SOLIDHIST" 1) (setvar "BLIPMODE" 0)
  (setvar "INSUNITS" 4)                       ; millimetres
  (command "_.UCS" "_W")

  ;; layers -----------------------------------------------------------
  (flm:layer "FLM-RAIL"      "150")   ; steel blue
  (flm:layer "FLM-PLATE"      "30")   ; orange
  (flm:layer "FLM-CLAMP"      "80")   ; green
  (flm:layer "FLM-CRUSH"       "8")   ; dark grey
  (flm:layer "FLM-FASTENER"  "251")   ; light grey
  (flm:layer "FLM-LED-REF"   "230")   ; magenta - reference, not made
  (flm:layer "FLM-CL"          "1")   ; centrelines

  (setq h (flm:rail-h))

  (princ "\nBuilding rail ...")
  (flm:make-rail)

  (princ "\nBuilding chassis plates ...")
  (foreach sx (list -1.0 1.0) (flm:make-plate sx))

  (princ "\nBuilding clamps ...")
  (foreach sx (list -1.0 1.0)
    (flm:make-saddle sx)
    (flm:make-strap  sx))

  (princ "\nBuilding crush tubes ...")
  (foreach sx (list -1.0 1.0)
    (foreach x (list (- *PLATE-CTR-X* (/ *PLATE-PITCH* 2.0))
                     (+ *PLATE-CTR-X* (/ *PLATE-PITCH* 2.0)))
      (flm:make-crush (* sx x) 0.0 *CRUSH-OD-M10* *PLATE-HOLE-D*))
    (foreach y (list (- 0.0 *CBOLT-Y*) *CBOLT-Y*)
      (flm:make-crush (* sx *CLAMP-X*) y *CRUSH-OD-M6* *CBOLT-D*)))

  (princ "\nPlacing fasteners and light bar ...")
  (foreach sx (list -1.0 1.0)
    (foreach x (list (- *PLATE-CTR-X* (/ *PLATE-PITCH* 2.0))
                     (+ *PLATE-CTR-X* (/ *PLATE-PITCH* 2.0)))
      (flm:make-bolt (* sx x) 0.0 5.0 (- 0.0 h *PLATE-T* 12.0) 10.0 17.0))
    (foreach y (list (- 0.0 *CBOLT-Y*) *CBOLT-Y*)
      (flm:make-bolt (* sx *CLAMP-X*) y (+ *SADDLE-H* *STRAP-H* 4.0)
                     (- 0.0 h 12.0) 6.0 10.0)))
  (flm:make-bar)

  (flm:clayer "0")
  (setvar "CMDECHO" oe) (setvar "OSMODE" oo)
  (setvar "3DOSMODE" o3) (setvar "OSNAPCOORD" oc)
  (setvar "SOLIDHIST" os) (setvar "BLIPMODE" ob)
  (command "_.ZOOM" "_E")
  (princ "\n--- FLM: assembly complete. Run FLMVIEWS or FLMINFO. ---")
  (princ)
)

;;; -------------------------------------------------------------------
;;;  VIEW SET-UP
;;; -------------------------------------------------------------------
(defun C:FLMVIEWS ( / oe)
  (setq oe (getvar "CMDECHO")) (setvar "CMDECHO" 0)
  (command "_.-VIEW" "_SWISO")
  (command "_.ZOOM" "_E")
  (command "_.VSCURRENT" "_Shaded")
  (setvar "CMDECHO" oe)
  (princ "\nSW isometric, shaded.")
  (princ)
)

;;; -------------------------------------------------------------------
;;;  MASS PROPERTIES REPORT
;;; -------------------------------------------------------------------
(defun C:FLMINFO ( / ss i e lay tbl hit tot v m oz)
  (flm:params)
  ;; rtos honours DIMZIN, and a drawing seeded from the A3 sheet carries a
  ;; dimension style that suppresses leading zeros - which turns 0.118 kg
  ;; into .118 in this table.  Force it off for the report only.
  (setq oz (getvar "DIMZIN"))
  (setvar "DIMZIN" 0)
  (setq ss (ssget "_X" '((0 . "3DSOLID"))) i 0 tot 0.0 tbl '())
  (if (null ss) (setq ss (ssadd)))
  ;; bucket the solids into one selection set per layer
  (while (< i (sslength ss))
    (setq e   (ssname ss i)
          lay (cdr (assoc 8 (entget e)))
          hit (assoc lay tbl))
    (if hit
      (progn (ssadd e (caddr hit))
             (setq tbl (subst (list lay (1+ (cadr hit)) (caddr hit)) hit tbl)))
      (setq tbl (cons (list lay 1 (ssadd e (ssadd))) tbl)))
    (setq i (1+ i))
  )
  (setq tbl (reverse tbl))
  (princ "\n\n  LAYER              QTY      VOLUME (cm3)     MASS (kg)")
  (princ "\n  -----------------------------------------------------------------")
  (foreach r tbl
    (setq v (flm:volume-ss (caddr r))
          m (/ (* v (flm:density (car r))) 1000.0))
    (princ (strcat "\n  " (car r)
                   (substr "                   " 1 (max 1 (- 19 (strlen (car r)))))
                   (itoa (cadr r))
                   "        " (rtos (/ v 1000.0) 2 1)
                   "          " (rtos m 2 3)))
    (if (not (member (car r) '("FLM-LED-REF" "FLM-FASTENER")))
        (setq tot (+ tot m)))
  )
  (princ (strcat "\n  -----------------------------------------------------------------"
                 "\n  Fabricated mass (excl. bar + fasteners): " (rtos tot 2 3) " kg\n"))
  (setvar "DIMZIN" oz)
  (princ)
)

(princ "\nfront_led_mount.lsp loaded.  Commands:  FLM  |  FLMVIEWS  |  FLMINFO\n")
(princ)

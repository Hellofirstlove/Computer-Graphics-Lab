#!/usr/bin/env python3
"""
2D Traffic Simulation — OpenGL / Python
=========================================
Controls:
  SPACE   Pause / Resume
  A       Add a random car
  R       Remove a car
  +  /  - Increase / Decrease green-light duration
  N       Toggle Day / Night mode
  Q       Quit
"""

from OpenGL.GL   import *
from OpenGL.GLUT import *
from OpenGL.GLU  import *
import math, random, sys

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
W, H   = 800, 800
CX, CY = W // 2, H // 2     # intersection centre  (400, 400)

HALF   = 80                  # road half-width  →  road spans CX±80 / CY±80
LANE   = 40                  # single lane width

# Lane centre coordinates
NB_X = CX + LANE             # 440  north-bound x  (cars go upward)
SB_X = CX - LANE             # 360  south-bound x  (cars go downward)
EB_Y = CY - LANE             # 360  east-bound  y  (cars go rightward)
WB_Y = CY + LANE             # 440  west-bound  y  (cars go leftward)

# Stop-line edges — car FRONT must not exceed these on red/yellow
NB_STOP = CY - HALF          # 320  NB cars approaching from below
SB_STOP = CY + HALF          # 480  SB cars approaching from above
EB_STOP = CX - HALF          # 320  EB cars approaching from left
WB_STOP = CX + HALF          # 480  WB cars approaching from right

CAR_L   = 36                 # car length  (along direction of travel)
CAR_W   = 20                 # car width
MIN_GAP = CAR_L + 14         # min centre-to-centre gap for same-lane cars

# ═══════════════════════════════════════════════════════════════════════════════
#  SIMULATION STATE
# ═══════════════════════════════════════════════════════════════════════════════
paused       = False
day_mode     = True

# Signal phase:  0=NS-green  1=NS-yellow  2=EW-green  3=EW-yellow
signal_phase = 0
signal_timer = 0
GREEN_DUR    = 180           # frames  (~3 s at 60 fps)
YELLOW_DUR   = 45

cars         = []
total_passed = 0             # bonus vehicle counter


# ─── static star field (generated once, lives in corner grass areas) ──────────
def _gen_stars(n=130):
    pts = []
    while len(pts) < n:
        sx, sy = random.randint(0, W), random.randint(0, H)
        on_h = (CY - HALF) <= sy <= (CY + HALF)
        on_v = (CX - HALF) <= sx <= (CX + HALF)
        if not on_h and not on_v:
            pts.append((sx, sy))
    return pts

_STARS = _gen_stars()


# ═══════════════════════════════════════════════════════════════════════════════
#  DRAWING PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════════
def fill_disk(cx, cy, r, segs=28):
    """Filled circle."""
    glBegin(GL_POLYGON)
    for i in range(segs):
        a = 2 * math.pi * i / segs
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()


def fill_rect(cx, cy, w, h):
    """Filled axis-aligned rectangle centred at (cx, cy)."""
    glBegin(GL_QUADS)
    glVertex2f(cx - w/2, cy - h/2)
    glVertex2f(cx + w/2, cy - h/2)
    glVertex2f(cx + w/2, cy + h/2)
    glVertex2f(cx - w/2, cy + h/2)
    glEnd()


def render_text(x, y, s, font=GLUT_BITMAP_HELVETICA_12):
    glRasterPos2f(x, y)
    for c in s:
        glutBitmapCharacter(font, ord(c))


# ─── line helpers ──────────────────────────────────────────────────────────────
def _hl(x0, x1, y):
    glBegin(GL_LINES); glVertex2f(x0, y); glVertex2f(x1, y); glEnd()

def _vl(y0, y1, x):
    glBegin(GL_LINES); glVertex2f(x, y0); glVertex2f(x, y1); glEnd()

def _dh(x0, x1, y, d=30, g=20):
    glBegin(GL_LINES)
    x = x0
    while x < x1:
        glVertex2f(x, y); glVertex2f(min(x + d, x1), y)
        x += d + g
    glEnd()

def _dv(y0, y1, x, d=30, g=20):
    glBegin(GL_LINES)
    y = y0
    while y < y1:
        glVertex2f(x, y); glVertex2f(x, min(y + d, y1))
        y += d + g
    glEnd()


# ═══════════════════════════════════════════════════════════════════════════════
#  CAR CLASS
# ═══════════════════════════════════════════════════════════════════════════════
_PALETTE = [
    (0.85, 0.15, 0.15), (0.15, 0.45, 0.90), (0.95, 0.70, 0.10),
    (0.15, 0.75, 0.25), (0.78, 0.22, 0.80), (0.95, 0.45, 0.05),
    (0.10, 0.78, 0.80), (0.55, 0.55, 0.95), (0.92, 0.92, 0.92),
    (0.60, 0.30, 0.10), (0.10, 0.60, 0.40), (0.90, 0.40, 0.50),
]

class Car:
    def __init__(self, direction=None):
        self.direction = direction or random.choice('NSEW')
        self.speed     = round(random.uniform(1.8, 3.0), 2)
        self.color     = random.choice(_PALETTE)
        self._spawn()

    # ── placement ─────────────────────────────────────────────────────────────
    def _spawn(self):
        off = random.randint(0, 240)     # stagger so cars don't all arrive together
        d   = self.direction
        if   d == 'N': self.x, self.y = NB_X, -(CAR_L + off)
        elif d == 'S': self.x, self.y = SB_X,  H + CAR_L + off
        elif d == 'E': self.x, self.y = -(CAR_L + off), EB_Y
        else:          self.x, self.y =  W + CAR_L + off, WB_Y

    # ── geometry ──────────────────────────────────────────────────────────────
    @property
    def front(self):
        """Leading-edge coordinate in direction of travel."""
        d = self.direction
        if d == 'N': return self.y + CAR_L / 2
        if d == 'S': return self.y - CAR_L / 2
        if d == 'E': return self.x + CAR_L / 2
        return              self.x - CAR_L / 2   # W

    # ── stop checks ───────────────────────────────────────────────────────────
    def _stop_for_signal(self, phase):
        """Return True if this car must halt at its stop line."""
        ns = (phase == 0)   # only phase 0 is NS-green
        ew = (phase == 2)   # only phase 2 is EW-green
        d  = self.direction
        if d == 'N' and not ns and self.front <= NB_STOP: return True
        if d == 'S' and not ns and self.front >= SB_STOP: return True
        if d == 'E' and not ew and self.front <= EB_STOP: return True
        if d == 'W' and not ew and self.front >= WB_STOP: return True
        return False

    def _stop_for_car(self, others):
        """Return True if a leading same-lane car is too close."""
        d = self.direction
        for o in others:
            if o is self or o.direction != d:
                continue
            if   d == 'N': gap = o.y - self.y
            elif d == 'S': gap = self.y - o.y
            elif d == 'E': gap = o.x - self.x
            else:          gap = self.x - o.x
            if 0 < gap < MIN_GAP:
                return True
        return False

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, others, phase):
        if self._stop_for_signal(phase) or self._stop_for_car(others):
            return                       # stay put this frame
        s = self.speed
        d = self.direction
        if   d == 'N': self.y += s
        elif d == 'S': self.y -= s
        elif d == 'E': self.x += s
        else:          self.x -= s

    def off_screen(self):
        m = 180
        return self.x < -m or self.x > W + m or self.y < -m or self.y > H + m

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self):
        d  = self.direction
        bw = CAR_W if d in ('N', 'S') else CAR_L
        bh = CAR_L if d in ('N', 'S') else CAR_W

        glPushMatrix()
        glTranslatef(self.x, self.y, 0)

        # — body —
        glColor3f(*self.color)
        fill_rect(0, 0, bw, bh)

        # — roof (darker stripe in the middle) —
        r, g, b = self.color
        glColor3f(r * 0.70, g * 0.70, b * 0.70)
        fill_rect(0, 0, bw * 0.68, bh * 0.52)

        # — windshield (light blue, at front of car) —
        glColor3f(0.55, 0.88, 1.0)
        ws = 0.28   # fraction of car length
        if   d == 'N': fill_rect( 0,  bh/2 - bh*ws/2, bw*0.66, bh*ws)
        elif d == 'S': fill_rect( 0, -bh/2 + bh*ws/2, bw*0.66, bh*ws)
        elif d == 'E': fill_rect( bw/2 - bw*ws/2, 0,  bw*ws,   bh*0.66)
        else:          fill_rect(-bw/2 + bw*ws/2, 0,  bw*ws,   bh*0.66)

        # — wheels (4 dark discs near corners) —
        glColor3f(0.12, 0.12, 0.12)
        if d in ('N', 'S'):
            wps = [(-bw/2, -bh*0.33), ( bw/2, -bh*0.33),
                   (-bw/2,  bh*0.33), ( bw/2,  bh*0.33)]
        else:
            wps = [(-bw*0.33, -bh/2), (-bw*0.33,  bh/2),
                   ( bw*0.33, -bh/2), ( bw*0.33,  bh/2)]
        for wx, wy in wps:
            fill_disk(wx, wy, 4)

        # — headlights (tiny yellow dots at the front edge) —
        glColor3f(1.0, 0.95, 0.5)
        if   d == 'N': hlps = [(-bw*0.24,  bh/2), (bw*0.24,  bh/2)]
        elif d == 'S': hlps = [(-bw*0.24, -bh/2), (bw*0.24, -bh/2)]
        elif d == 'E': hlps = [( bw/2, -bh*0.24), ( bw/2,  bh*0.24)]
        else:          hlps = [(-bw/2, -bh*0.24), (-bw/2,  bh*0.24)]
        for hx, hy in hlps:
            fill_disk(hx, hy, 3, segs=10)

        glPopMatrix()


# ═══════════════════════════════════════════════════════════════════════════════
#  TRAFFIC LIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
def draw_signal(bx, by, for_ns, phase):
    """
    Vertical 3-lamp traffic light.
    bx, by = bottom-left corner of the pole base.
    for_ns : True  → controls North/South traffic
             False → controls East/West  traffic
    """
    PH, BH = 50, 60            # pole height, box height

    # pole
    glColor3f(0.22, 0.22, 0.22)
    fill_rect(bx + 6, by + PH / 2, 9, PH)

    # housing box
    glColor3f(0.10, 0.10, 0.10)
    fill_rect(bx + 6, by + PH + BH / 2, 18, BH)

    # determine which lamps are lit
    if for_ns:
        red_on = phase in (2, 3)
        yel_on = phase == 1
        grn_on = phase == 0
    else:
        red_on = phase in (0, 1)
        yel_on = phase == 3
        grn_on = phase == 2

    cy_r = by + PH + BH - 12
    cy_y = by + PH + BH // 2
    cy_g = by + PH + 12

    # red lamp
    glColor3f(0.90 if red_on else 0.20, 0.04, 0.04)
    fill_disk(bx + 6, cy_r, 6)

    # yellow lamp
    glColor3f(0.88 if yel_on else 0.20,
              0.88 if yel_on else 0.20, 0.04)
    fill_disk(bx + 6, cy_y, 6)

    # green lamp
    glColor3f(0.04, 0.90 if grn_on else 0.20, 0.04)
    fill_disk(bx + 6, cy_g, 6)

    # soft glow around the active lamp
    if red_on:
        glColor4f(1.0, 0.0, 0.0, 0.22); fill_disk(bx + 6, cy_r, 11)
    if yel_on:
        glColor4f(1.0, 1.0, 0.0, 0.22); fill_disk(bx + 6, cy_y, 11)
    if grn_on:
        glColor4f(0.0, 1.0, 0.0, 0.22); fill_disk(bx + 6, cy_g, 11)


# ═══════════════════════════════════════════════════════════════════════════════
#  CORNER DECORATIONS  (buildings + trees)
# ═══════════════════════════════════════════════════════════════════════════════
def _decor(cx, cy):
    """Small building with 4 windows + 2 flanking trees."""
    # building body
    if day_mode:
        glColor3f(0.68, 0.62, 0.54)
    else:
        glColor3f(0.18, 0.16, 0.14)
    fill_rect(cx, cy, 56, 56)

    # windows (lit yellow at night)
    if day_mode:
        glColor3f(0.52, 0.84, 1.0)
    else:
        glColor3f(1.0, 0.82, 0.28)
    for dx, dy in [(-13, 14), (13, 14), (-13, -6), (13, -6)]:
        fill_rect(cx + dx, cy + dy, 9, 9)

    # flanking trees
    for side in (-1, 1):
        tx = cx + side * 44
        # trunk
        glColor3f(0.38, 0.26, 0.08)
        fill_rect(tx, cy - 20, 7, 22)
        # canopy
        if day_mode:
            glColor3f(0.18, 0.54, 0.14)
        else:
            glColor3f(0.05, 0.20, 0.05)
        fill_disk(tx, cy - 2, 17)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════
def draw_environment():
    # ── background ────────────────────────────────────────────────────────────
    if day_mode:
        glColor3f(0.27, 0.52, 0.17)
    else:
        glColor3f(0.03, 0.05, 0.03)
    fill_rect(W / 2, H / 2, float(W), float(H))

    # night-mode stars
    if not day_mode:
        glColor3f(0.90, 0.90, 0.85)
        for sx, sy in _STARS:
            fill_disk(sx, sy, 1.3, segs=5)

    # ── road slabs ────────────────────────────────────────────────────────────
    if day_mode:
        glColor3f(0.30, 0.30, 0.30)
    else:
        glColor3f(0.15, 0.15, 0.15)
    fill_rect(W / 2, CY, float(W), HALF * 2)    # horizontal road
    fill_rect(CX, H / 2, HALF * 2, float(H))    # vertical road

    # intersection box (slightly lighter)
    if day_mode:
        glColor3f(0.36, 0.36, 0.36)
    else:
        glColor3f(0.22, 0.22, 0.22)
    fill_rect(CX, CY, HALF * 2 + 1, HALF * 2 + 1)

    # ── lane markings ─────────────────────────────────────────────────────────
    glLineWidth(2.0)

    # yellow centre dashes (only outside the intersection box)
    glColor3f(1.0, 1.0, 0.0)
    _dh(0,         CX - HALF, CY)
    _dh(CX + HALF, W,         CY)
    _dv(0,         CY - HALF, CX)
    _dv(CY + HALF, H,         CX)

    # white road-edge lines
    glColor3f(1.0, 1.0, 1.0)
    for x0, x1 in [(0, CX - HALF), (CX + HALF, W)]:
        _hl(x0, x1, CY - HALF)
        _hl(x0, x1, CY + HALF)
    for y0, y1 in [(0, CY - HALF), (CY + HALF, H)]:
        _vl(y0, y1, CX - HALF)
        _vl(y0, y1, CX + HALF)

    # stop lines (thick white, one per lane)
    glLineWidth(3.5)
    _hl(CX,        CX + HALF, CY - HALF)   # NB stop  (right half = NB lane)
    _hl(CX - HALF, CX,        CY + HALF)   # SB stop  (left  half = SB lane)
    _vl(CY - HALF, CY,        CX - HALF)   # EB stop  (bottom half = EB lane)
    _vl(CY,        CY + HALF, CX + HALF)   # WB stop  (top    half = WB lane)
    glLineWidth(1.0)

    # ── zebra crossings (white stripes just outside each intersection edge) ────
    glColor3f(0.88, 0.88, 0.88)
    s = 10
    for i in range(20):
        x = CX - HALF + i * s * 2
        if x + s > CX + HALF:
            break
        fill_rect(x + s / 2, CY - HALF - 14, s, 20)   # south crossing
        fill_rect(x + s / 2, CY + HALF + 14, s, 20)   # north crossing
    for i in range(20):
        y = CY - HALF + i * s * 2
        if y + s > CY + HALF:
            break
        fill_rect(CX - HALF - 14, y + s / 2, 20, s)   # west  crossing
        fill_rect(CX + HALF + 14, y + s / 2, 20, s)   # east  crossing

    # ── traffic lights at all 4 corners ───────────────────────────────────────
    p = 6                                           # padding from road edge
    # SE corner — NS direction (faces northbound cars)
    draw_signal(CX + HALF + p,        CY - HALF - 116, True,  signal_phase)
    # NW corner — NS direction (faces southbound cars)
    draw_signal(CX - HALF - p - 18,   CY + HALF + p,   True,  signal_phase)
    # NE corner — EW direction (faces westbound cars)
    draw_signal(CX + HALF + p,        CY + HALF + p,   False, signal_phase)
    # SW corner — EW direction (faces eastbound cars)
    draw_signal(CX - HALF - p - 18,   CY - HALF - 116, False, signal_phase)

    # ── corner decorations ────────────────────────────────────────────────────
    lx  = (CX - HALF) // 2              # 160  midpoint of left grass
    rx  = (CX + HALF + W) // 2          # 640  midpoint of right grass
    bot = (CY - HALF) // 2              # 160  midpoint of bottom grass
    top = (CY + HALF + H) // 2          # 640  midpoint of top grass
    _decor(lx,  top)
    _decor(rx,  top)
    _decor(lx,  bot)
    _decor(rx,  bot)


# ═══════════════════════════════════════════════════════════════════════════════
#  HUD  (heads-up display)
# ═══════════════════════════════════════════════════════════════════════════════
def draw_hud():
    # top info bar
    glColor4f(0.0, 0.0, 0.0, 0.62)
    fill_rect(W / 2, H - 22, float(W), 44)

    # bottom controls hint
    glColor4f(0.0, 0.0, 0.0, 0.55)
    fill_rect(W / 2, 16, float(W), 32)

    glColor3f(0.95, 0.88, 0.40)
    render_text(8, 9,
        "SPACE=Pause  A=Add Car  R=Remove  +/-=Signal Time  N=Night/Day  Q=Quit")

    # signal phase label + colour
    labels = ["NS  GREEN", "NS YELLOW", "EW  GREEN", "EW YELLOW"]
    cols   = [(0.2,1.0,0.2),(1.0,1.0,0.1),(0.2,1.0,0.2),(1.0,1.0,0.1)]
    glColor3f(*cols[signal_phase])
    render_text(8, H - 14,
        f"Signal: {labels[signal_phase]}   "
        f"Green: {GREEN_DUR} fr ({GREEN_DUR/60:.1f}s)")

    # vehicle stats
    glColor3f(0.90, 0.90, 0.90)
    mode_str = "Day" if day_mode else "Night"
    render_text(W - 330, H - 14,
        f"Cars on road: {len(cars):3d}   "
        f"Total passed: {total_passed:4d}   "
        f"Mode: {mode_str}")

    # paused overlay
    if paused:
        glColor4f(0.0, 0.0, 0.0, 0.52)
        fill_rect(W / 2, H / 2, 230, 60)
        glColor3f(1.0, 0.30, 0.30)
        render_text(W / 2 - 65, H / 2 + 10,
                    "--- PAUSED ---", GLUT_BITMAP_HELVETICA_18)
        glColor3f(0.80, 0.80, 0.80)
        render_text(W / 2 - 65, H / 2 - 10, "Press SPACE to resume")


# ═══════════════════════════════════════════════════════════════════════════════
#  GLUT CALLBACKS
# ═══════════════════════════════════════════════════════════════════════════════
def display():
    if day_mode:
        glClearColor(0.27, 0.52, 0.17, 1.0)
    else:
        glClearColor(0.03, 0.05, 0.03, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)

    draw_environment()

    for car in cars:
        car.draw()

    draw_hud()
    glutSwapBuffers()


def update_sim(value):
    global signal_phase, signal_timer, total_passed

    if not paused:
        # ── advance signal phase ───────────────────────────────────────────────
        signal_timer += 1
        if signal_phase == 0 and signal_timer >= GREEN_DUR:
            signal_phase, signal_timer = 1, 0
        elif signal_phase == 1 and signal_timer >= YELLOW_DUR:
            signal_phase, signal_timer = 2, 0
        elif signal_phase == 2 and signal_timer >= GREEN_DUR:
            signal_phase, signal_timer = 3, 0
        elif signal_phase == 3 and signal_timer >= YELLOW_DUR:
            signal_phase, signal_timer = 0, 0

        # ── update cars ────────────────────────────────────────────────────────
        for car in cars[:]:
            car.update(cars, signal_phase)
            if car.off_screen():
                total_passed += 1
                cars.remove(car)
                cars.append(Car(car.direction))   # respawn in same lane

    glutPostRedisplay()
    glutTimerFunc(16, update_sim, 0)    # ~62 fps


def keyboard(key, x, y):
    global paused, day_mode, GREEN_DUR

    if   key == b' ':          paused    = not paused
    elif key in (b'a', b'A'): cars.append(Car())
    elif key in (b'r', b'R') and cars: cars.pop()
    elif key in (b'+', b'='): GREEN_DUR = min(GREEN_DUR + 20, 500)
    elif key in (b'-', b'_'): GREEN_DUR = max(GREEN_DUR - 20,  40)
    elif key in (b'n', b'N'): day_mode  = not day_mode
    elif key in (b'q', b'Q'): sys.exit(0)

    glutPostRedisplay()


# ═══════════════════════════════════════════════════════════════════════════════
#  INITIALISATION & ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
def init_gl():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, W, 0, H, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # blending for glow + semi-transparent HUD overlays
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # spawn initial fleet: 3 cars per direction, staggered by random offset
    for d in list('NNN' 'SSS' 'EEE' 'WWW'):
        cars.append(Car(d))


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(W, H)
    glutInitWindowPosition(60, 60)
    glutCreateWindow(b"2D Traffic Simulation  --  OpenGL / Python")
    init_gl()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(16, update_sim, 0)
    glutMainLoop()


if __name__ == "__main__":
    main()
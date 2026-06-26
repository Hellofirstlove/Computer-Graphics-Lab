"""
╔══════════════════════════════════════════════════════════════╗
║       2D Traffic Simulation — OpenGL / PyOpenGL              ║
║  ──────────────────────────────────────────────────────────  ║
║  Keys:  S = Pause/Resume    A = Add car                      ║
║         N = Day/Night       + / - = Green signal duration    ║
║         Q = Quit                                             ║
╚══════════════════════════════════════════════════════════════╝
"""

from OpenGL.GL   import *
from OpenGL.GLUT import *
from OpenGL.GLU  import *
import math, random, sys

# ═══════════════════════════════════════════ Constants & globals ═════════════
W, H   = 900, 900
CX, CY = 450, 450
RW     = 130

RED, YELLOW, GREEN   = 0, 1, 2
RIGHT, LEFT, UP, DOWN = 0, 1, 2, 3

paused        = False
day_mode      = True
cars          = []
total_spawned = 0
frame_no      = 0

green_dur  = 200
yellow_dur = 50

sig_phase  = 0
sig_timer  = 0
h_sig      = GREEN
v_sig      = RED

STOP_LINES = {}

# ── Lane centres: [inner_lane, outer_lane] per direction ─────────────────────
# Each road half is 130 px wide; split into two 65 px lanes.
LANES = {
    RIGHT: [CY - RW//4,      CY - 3*RW//4   ],   # y positions
    LEFT:  [CY + RW//4,      CY + 3*RW//4   ],
    UP:    [CX + RW//4,      CX + 3*RW//4   ],   # x positions
    DOWN:  [CX - RW//4,      CX - 3*RW//4   ],
}
TURN_MAP = {
    (RIGHT, 'left'): UP,    (RIGHT, 'right'): DOWN,
    (LEFT,  'left'): DOWN,  (LEFT,  'right'): UP,
    (UP,    'left'): LEFT,  (UP,    'right'): RIGHT,
    (DOWN,  'left'): RIGHT, (DOWN,  'right'): LEFT,
}
ENTRY_LANE = {
    RIGHT: ('y', CY - RW // 4),
    LEFT:  ('y', CY + RW // 4),
    UP:    ('x', CX + RW // 4),
    DOWN:  ('x', CX - RW // 4),
}
DIR_ANGLE   = {RIGHT: 0, UP: 90, LEFT: 180, DOWN: 270}
RIGHT_VEC   = {RIGHT: (0,-1), LEFT: (0,1), UP: (1,0), DOWN: (-1,0)}
LEFT_VEC    = {RIGHT: (0,1), LEFT: (0,-1), UP: (-1,0), DOWN: (1,0)}
TURN_RADIUS = RW // 2
TURN_SPEED  = 0.028

# ═══════════════════════════════════════════ Low-level GL primitives ═════════
def filled_circle(cx, cy, r, segs=28):
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(cx, cy)
    for i in range(segs + 1):
        a = 2 * math.pi * i / segs
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()

def filled_rect(x, y, w, h):
    glBegin(GL_QUADS)
    glVertex2f(x,   y);   glVertex2f(x+w, y)
    glVertex2f(x+w, y+h); glVertex2f(x,   y+h)
    glEnd()

def draw_text(x, y, s, font=GLUT_BITMAP_HELVETICA_12):
    glRasterPos2f(x, y)
    for ch in s:
        glutBitmapCharacter(font, ord(ch))

def arc(cx, cy, r, a1, a2, segs=30):
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(cx, cy)
    for i in range(segs + 1):
        a = math.radians(a1 + (a2 - a1) * i / segs)
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()

# ═══════════════════════════════════════════ Car class ═══════════════════════
_CAR_COLORS = [
    (0.92, 0.18, 0.18), (0.20, 0.45, 0.92), (0.92, 0.72, 0.08),
    (0.25, 0.80, 0.30), (0.92, 0.50, 0.10), (0.70, 0.25, 0.80),
    (0.15, 0.80, 0.80), (0.95, 0.95, 0.95), (0.55, 0.35, 0.10),
]

class Car:
    CW = 42
    CH = 22

    def __init__(self, x, y, direction):
        global total_spawned
        total_spawned += 1
        self.x       = float(x)
        self.y       = float(y)
        self.dir     = direction
        self.spd     = random.uniform(1.8, 3.0)
        self.col     = random.choice(_CAR_COLORS)
        self.stopped = False
        self.active  = True

        # ── Turn state ────────────────────────────────────────────────────
        self.lane        = 0
        self.turn_intent = random.choice(['straight']*5 + ['left', 'right'])
        self.turned      = False
        self.turning     = False
        self.turn_progress = 0.0
        self.turn_cx = self.turn_cy = 0.0
        self.turn_a0 = self.turn_a1 = 0.0
        self.turn_new_dir = direction
        self.heading = float(DIR_ANGLE[direction])

    # ── Geometry helpers ─────────────────────────────────────────────────────
    def front(self):
        hw = self.CW / 2
        if   self.dir == RIGHT: return self.x + hw
        elif self.dir == LEFT:  return self.x - hw
        elif self.dir == UP:    return self.y + hw
        else:                   return self.y - hw

    # ── Turn logic ─────────────────────────────────────────────────────────────
    def check_turn(self):
        if self.turn_intent == 'straight' or self.turned:
            return
        in_box = (CX - RW < self.x < CX + RW and CY - RW < self.y < CY + RW)
        if not in_box:
            return
        # Trigger point inside intersection
        ok = False
        if   self.dir == RIGHT and self.x >= CX - RW // 3: ok = True
        elif self.dir == LEFT  and self.x <= CX + RW // 3: ok = True
        elif self.dir == UP    and self.y >= CY - RW // 3: ok = True
        elif self.dir == DOWN  and self.y <= CY + RW // 3: ok = True
        if not ok:
            return
        new_dir = TURN_MAP[(self.dir, self.turn_intent)]
        axis, lane_pos = ENTRY_LANE[new_dir]
        # Safety: check target lane is clear
        SAFE_GAP = self.CW + 45
        for ot in cars:
            if ot is self or not ot.active or ot.dir != new_dir:
                continue
            if new_dir in (RIGHT, LEFT):
                if abs(ot.y - lane_pos) < self.CH and abs(ot.x - self.x) < SAFE_GAP:
                    return
            else:
                if abs(ot.x - lane_pos) < self.CH and abs(ot.y - self.y) < SAFE_GAP:
                    return
        # Also check oncoming cars for left turns
        if self.turn_intent == 'left':
            opp = {RIGHT: LEFT, LEFT: RIGHT, UP: DOWN, DOWN: UP}
            for ot in cars:
                if ot is self or not ot.active or ot.dir != opp[self.dir]:
                    continue
                if abs(ot.x - self.x) < SAFE_GAP and abs(ot.y - self.y) < SAFE_GAP:
                    return
        # Start smooth arc turn
        R = TURN_RADIUS
        if self.turn_intent == 'right':
            rv = RIGHT_VEC[self.dir]
            self.turn_cx = self.x + R * rv[0]
            self.turn_cy = self.y + R * rv[1]
        else:
            lv = LEFT_VEC[self.dir]
            self.turn_cx = self.x + R * lv[0]
            self.turn_cy = self.y + R * lv[1]
        self.turn_a0 = math.degrees(math.atan2(self.y - self.turn_cy, self.x - self.turn_cx))
        self.turn_a1 = self.turn_a0 + (-90 if self.turn_intent == 'right' else 90)
        self.turn_new_dir = new_dir
        self.turning = True
        self.turn_progress = 0.0

    # ── Arc interpolation ──────────────────────────────────────────────────
    def update_turn(self):
        self.turn_progress += TURN_SPEED
        if self.turn_progress >= 1.0:
            self.turn_progress = 1.0
            a = math.radians(self.turn_a1)
            self.x = self.turn_cx + TURN_RADIUS * math.cos(a)
            self.y = self.turn_cy + TURN_RADIUS * math.sin(a)
            self.dir = self.turn_new_dir
            self.heading = float(DIR_ANGLE[self.dir])
            self.turned = True
            self.turning = False
            return
        t = self.turn_progress
        t = t * t * (3 - 2 * t)   # smoothstep easing
        cur_a = math.radians(self.turn_a0 + (self.turn_a1 - self.turn_a0) * t)
        self.x = self.turn_cx + TURN_RADIUS * math.cos(cur_a)
        self.y = self.turn_cy + TURN_RADIUS * math.sin(cur_a)
        start_h = DIR_ANGLE[self.dir]
        end_h   = DIR_ANGLE[self.turn_new_dir]
        diff = end_h - start_h
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        self.heading = start_h + diff * t

    # ── Movement ─────────────────────────────────────────────────────────────
    def move(self):
        if not self.active:
            return
        # Check for turn at intersection
        self.check_turn()
        if self.turning:
            self.update_turn()
        elif not self.stopped:
            if   self.dir == RIGHT: self.x += self.spd
            elif self.dir == LEFT:  self.x -= self.spd
            elif self.dir == UP:    self.y += self.spd
            else:                   self.y -= self.spd
        margin = 90
        if (self.x < -margin or self.x > W + margin or
                self.y < -margin or self.y > H + margin):
            self.active = False

    # ── Rendering ────────────────────────────────────────────────────────────
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, 0)

        glRotatef(self.heading, 0, 0, 1)

        hw, hh = self.CW / 2, self.CH / 2
        r, g, b = self.col

        glColor3f(r, g, b)
        filled_rect(-hw, -hh, self.CW, self.CH)

        glColor3f(r * 0.60, g * 0.60, b * 0.60)
        filled_rect(-hw * 0.42, -hh + 3, self.CW * 0.42, self.CH - 6)

        glColor3f(0.55, 0.83, 1.0)
        filled_rect(-hw * 0.41, -hh + 4, self.CW * 0.40, self.CH - 8)

        glColor3f(0.10, 0.10, 0.10)
        for wx, wy in [(-hw+8, -hh), (-hw+8, hh), (hw-8, -hh), (hw-8, hh)]:
            filled_circle(wx, wy, 5)
        glColor3f(0.45, 0.45, 0.45)
        for wx, wy in [(-hw+8, -hh), (-hw+8, hh), (hw-8, -hh), (hw-8, hh)]:
            filled_circle(wx, wy, 2.5)

        glColor3f(1.0, 1.0, 0.70)
        filled_rect(hw - 5, -hh + 3, 5, 5)
        filled_rect(hw - 5,  hh - 8, 5, 5)

        if not day_mode:
            glColor4f(1.0, 1.0, 0.7, 0.08)
            arc(hw, -hh + 5.5, 55, -25, 25, 12)
            arc(hw,  hh - 5.5, 55, -25, 25, 12)

        glColor3f(0.85, 0.10, 0.10)
        filled_rect(-hw, -hh + 3, 5, 5)
        filled_rect(-hw,  hh - 8, 5, 5)

        # Turn signal indicator
        if self.turn_intent == 'left' and not self.turned:
            glColor3f(1.0, 0.8, 0.0)
            filled_circle(-3, hh - 2, 3, 6)
        elif self.turn_intent == 'right' and not self.turned:
            glColor3f(1.0, 0.8, 0.0)
            filled_circle(-3, -hh + 2, 3, 6)

        glPopMatrix()

# ═══════════════════════════════════════════ Traffic light ═══════════════════
def draw_traffic_light(px, py, sig):
    glColor3f(0.22, 0.22, 0.22)
    filled_rect(px - 3, py, 6, 52)
    glColor3f(0.10, 0.10, 0.10)
    filled_rect(px - 14, py + 52, 28, 60)

    on, off = 1.0, 0.20
    glColor3f(on if sig == RED    else off, 0.0, 0.0)
    filled_circle(px, py + 100, 10)
    yv = on if sig == YELLOW else off
    glColor3f(yv, yv, 0.0)
    filled_circle(px, py + 82,  10)
    glColor3f(0.0, on if sig == GREEN else off, 0.0)
    filled_circle(px, py + 64,  10)

    if not day_mode:
        if   sig == RED:    glColor4f(1.0, 0.0, 0.0, 0.18); filled_circle(px, py+100, 24)
        elif sig == YELLOW: glColor4f(1.0, 1.0, 0.0, 0.15); filled_circle(px, py+ 82, 24)
        elif sig == GREEN:  glColor4f(0.0, 1.0, 0.0, 0.15); filled_circle(px, py+ 64, 24)

# ═══════════════════════════════════════════ Environment drawing ══════════════
def draw_road():
    gc = (0.22, 0.55, 0.22) if day_mode else (0.04, 0.11, 0.04)
    glColor3f(*gc)
    filled_rect(0, 0, W, H)

    if not day_mode:
        glColor3f(1.0, 1.0, 0.90)
        rng = random.Random(7)
        for _ in range(110):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            if abs(sy - CY) > RW and abs(sx - CX) > RW:
                filled_circle(sx, sy, 1.2, 6)

    rc = (0.30, 0.30, 0.30) if day_mode else (0.17, 0.17, 0.17)
    glColor3f(*rc)
    filled_rect(0,      CY - RW, W,    RW * 2)
    filled_rect(CX - RW, 0,      RW*2, H     )

    glColor3f(0.75, 0.72, 0.60)
    glLineWidth(2.5)
    for yy in (CY - RW, CY + RW):
        glBegin(GL_LINES); glVertex2f(0,     yy); glVertex2f(CX-RW, yy); glEnd()
        glBegin(GL_LINES); glVertex2f(CX+RW, yy); glVertex2f(W,     yy); glEnd()
    for xx in (CX - RW, CX + RW):
        glBegin(GL_LINES); glVertex2f(xx, 0);     glVertex2f(xx, CY-RW); glEnd()
        glBegin(GL_LINES); glVertex2f(xx, CY+RW); glVertex2f(xx, H);     glEnd()
    glLineWidth(1)

    glColor3f(1.0, 1.0, 0.0)
    glLineWidth(2)
    glEnable(GL_LINE_STIPPLE); glLineStipple(3, 0x0F0F)
    glBegin(GL_LINES); glVertex2f(0,     CY); glVertex2f(CX-RW, CY); glEnd()
    glBegin(GL_LINES); glVertex2f(CX+RW, CY); glVertex2f(W,     CY); glEnd()
    glBegin(GL_LINES); glVertex2f(CX, 0);     glVertex2f(CX, CY-RW); glEnd()
    glBegin(GL_LINES); glVertex2f(CX, CY+RW); glVertex2f(CX, H);     glEnd()
    glDisable(GL_LINE_STIPPLE); glLineWidth(1)

    # ── Inner-lane dashes (now 4 per road half, matching LANES centres) ──
    glColor3f(0.88, 0.88, 0.88)
    glLineWidth(1.5)
    glEnable(GL_LINE_STIPPLE); glLineStipple(2, 0x00FF)
    half = RW // 2
    for yy in (CY - half, CY + half):
        glBegin(GL_LINES); glVertex2f(0,     yy); glVertex2f(CX-RW, yy); glEnd()
        glBegin(GL_LINES); glVertex2f(CX+RW, yy); glVertex2f(W,     yy); glEnd()
    for xx in (CX - half, CX + half):
        glBegin(GL_LINES); glVertex2f(xx, 0);     glVertex2f(xx, CY-RW); glEnd()
        glBegin(GL_LINES); glVertex2f(xx, CY+RW); glVertex2f(xx, H);     glEnd()
    glDisable(GL_LINE_STIPPLE); glLineWidth(1)

    glColor3f(0.92, 0.92, 0.92)
    stripe, gap = 12, 7
    n = int(RW * 2 // (stripe + gap))
    for i in range(n):
        ox = CX - RW + i * (stripe + gap)
        filled_rect(ox, CY + RW + 4,  stripe, 20)
        filled_rect(ox, CY - RW - 24, stripe, 20)
    for i in range(n):
        oy = CY - RW + i * (stripe + gap)
        filled_rect(CX - RW - 24, oy, 20, stripe)
        filled_rect(CX + RW + 4,  oy, 20, stripe)

    glColor3f(0.95, 0.95, 0.95)
    glLineWidth(3)
    sl = STOP_LINES
    glBegin(GL_LINES); glVertex2f(sl[RIGHT], CY-RW); glVertex2f(sl[RIGHT], CY);     glEnd()
    glBegin(GL_LINES); glVertex2f(sl[LEFT],  CY);    glVertex2f(sl[LEFT],  CY+RW);  glEnd()
    glBegin(GL_LINES); glVertex2f(CX,        sl[UP]); glVertex2f(CX+RW,   sl[UP]);  glEnd()
    glBegin(GL_LINES); glVertex2f(CX-RW,    sl[DOWN]); glVertex2f(CX,     sl[DOWN]);glEnd()
    glLineWidth(1)

def draw_buildings():
    night_f = 0.38 if not day_mode else 1.0
    defs = [
        (30,          CY+RW+8,    90, 115, .65, .52, .40),
        (150,         CY+RW+8,    70,  85, .50, .45, .65),
        (245,         CY+RW+30,   80,  60, .40, .60, .55),
        (345,         CY+RW+15,   55,  95, .55, .40, .60),
        (CX+RW+10,   CY+RW+8,    90, 115, .65, .40, .40),
        (CX+RW+125,  CY+RW+8,    70,  85, .40, .65, .45),
        (CX+RW+215,  CY+RW+30,   80,  60, .55, .55, .40),
        (30,          30,         90, 115, .50, .50, .65),
        (150,         30,         70,  85, .65, .55, .40),
        (245,         50,         80,  60, .40, .55, .60),
        (CX+RW+10,   30,         90, 115, .45, .55, .65),
        (CX+RW+125,  50,         70,  85, .65, .65, .40),
    ]
    for bx, by, bw, bh, cr, cg, cb in defs:
        glColor3f(cr*night_f, cg*night_f, cb*night_f)
        filled_rect(bx, by, bw, bh)
        wc = (1.0, .95, .60) if not day_mode else (.70, .85, 1.0)
        glColor3f(*wc)
        for row in range(4):
            for col in range(2):
                wx = bx + 8 + col * (bw // 2 - 2)
                wy = by + 12 + row * 25
                if wy + 14 < by + bh - 5:
                    filled_rect(wx, wy, bw // 4, 14)
        glColor3f(cr*night_f*.65, cg*night_f*.65, cb*night_f*.65)
        glBegin(GL_TRIANGLES)
        glVertex2f(bx,        by + bh)
        glVertex2f(bx + bw,   by + bh)
        glVertex2f(bx+bw//2,  by + bh + 26)
        glEnd()

def draw_trees():
    pts = [
        (CX-RW-28, CY+RW+14), (CX-RW-28, CY-RW-40),
        (CX+RW+28, CY+RW+14), (CX+RW+28, CY-RW-40),
        (22,        CY+RW+14), (22,        CY-RW-40),
        (W-22,      CY+RW+14), (W-22,      CY-RW-40),
        (CX-RW-28,  H-35),     (CX+RW+28,  H-35),
        (CX-RW-28,  52),       (CX+RW+28,  52),
    ]
    for tx, ty in pts:
        glColor3f(.38, .24, .10)
        filled_rect(tx-4, ty-22, 8, 22)
        fc = (.10, .58, .10) if day_mode else (.04, .17, .04)
        glColor3f(*fc)
        filled_circle(tx,    ty+15, 19)
        filled_circle(tx-13, ty+4,  14)
        filled_circle(tx+13, ty+4,  14)

def draw_street_lamps():
    lamp_pts = [
        (CX-RW-12, CY+RW+2), (CX+RW+12, CY+RW+2),
        (CX-RW-12, CY-RW-2), (CX+RW+12, CY-RW-2),
    ]
    for lx, ly in lamp_pts:
        sign = 1 if ly > CY else -1
        glColor3f(0.45, 0.45, 0.45)
        filled_rect(lx-2, ly, 4, sign*35)
        glColor3f(0.3, 0.3, 0.3)
        filled_rect(lx-7, ly+sign*35, 14, sign*5)
        glColor3f(1.0, 0.95, 0.70)
        filled_circle(lx, ly + sign*37, 4)
        if not day_mode:
            glColor4f(1.0, 0.95, 0.60, 0.12)
            filled_circle(lx, ly + sign*37, 55)

# ═══════════════════════════════════════════ Signal state machine ════════════
def update_signals():
    global sig_phase, sig_timer, h_sig, v_sig
    sig_timer += 1
    if sig_phase == 0:
        h_sig, v_sig = GREEN, RED
        if sig_timer >= green_dur:  sig_phase, sig_timer = 1, 0
    elif sig_phase == 1:
        h_sig, v_sig = YELLOW, RED
        if sig_timer >= yellow_dur: sig_phase, sig_timer = 2, 0
    elif sig_phase == 2:
        h_sig, v_sig = RED, GREEN
        if sig_timer >= green_dur:  sig_phase, sig_timer = 3, 0
    elif sig_phase == 3:
        h_sig, v_sig = RED, YELLOW
        if sig_timer >= yellow_dur: sig_phase, sig_timer = 0, 0

# ═══════════════════════════════════════════ Car AI ══════════════════════════
def should_stop_signal(car):
    sig = h_sig if car.dir in (RIGHT, LEFT) else v_sig
    if sig == GREEN:
        return False
    sl, f = STOP_LINES[car.dir], car.front()
    if car.dir == RIGHT: return sl - 120 < f < sl
    if car.dir == LEFT:  return sl < f < sl + 120
    if car.dir == UP:    return sl - 120 < f < sl
    return                      sl < f < sl + 120

def should_stop_following(car):
    """
    Stops a car if another car ahead in the same lane is too close.
    Uses the car's CURRENT lateral position so lane-changing cars
    only get blocked by cars actually in their new path.
    """
    GAP = Car.CW + 22
    my_lat = car.y if car.dir in (RIGHT, LEFT) else car.x

    for ot in cars:
        if ot is car or not ot.active or ot.dir != car.dir:
            continue

        # Lateral overlap: compare actual positions (handles mid-lane-change)
        ot_lat = ot.y if car.dir in (RIGHT, LEFT) else ot.x
        if abs(ot_lat - my_lat) >= Car.CH:
            continue

        # Longitudinal: is ot directly ahead and too close?
        if car.dir == RIGHT and 0 < ot.x - car.x < GAP: return True
        if car.dir == LEFT  and 0 < car.x - ot.x < GAP: return True
        if car.dir == UP    and 0 < ot.y - car.y < GAP: return True
        if car.dir == DOWN  and 0 < car.y - ot.y < GAP: return True

    return False

def spawn_car():
    """
    Spawn a car at one of 8 positions (2 lanes × 4 directions).
    Car's lateral position is set to the chosen lane centre.
    """
    d        = random.choice([RIGHT, LEFT, UP, DOWN])
    lane_idx = random.randint(0, 1)
    lat      = LANES[d][lane_idx]

    if   d == RIGHT: x, y = -Car.CW,   lat
    elif d == LEFT:  x, y = W+Car.CW,  lat
    elif d == UP:    x, y = lat,       -Car.CW
    else:            x, y = lat,        H+Car.CW

    for c in cars:
        if abs(c.x - x) < 80 and abs(c.y - y) < 80:
            return

    car             = Car(x, y, d)
    car.lane        = lane_idx
    car.lateral     = float(lat)
    car.target_lateral = float(lat)

    # Sync the actual axis position to the chosen lane
    if d in (RIGHT, LEFT):
        car.y = float(lat)
    else:
        car.x = float(lat)

    cars.append(car)

# ═══════════════════════════════════════════ HUD ═════════════════════════════
_SIG_NAMES  = ['RED', 'YEL', 'GRN']
_SIG_COLORS = [(1, .2, .2), (.95, .95, .2), (.2, 1, .2)]

def draw_hud():
    glColor4f(0, 0, 0, 0.65)
    filled_rect(5, H - 150, 338, 144)

    def txt(x, y, s, c=(1, 1, 1)):
        glColor3f(*c); draw_text(x, y, s)

    active = sum(1 for c in cars if c.active)
    turning = sum(1 for c in cars if c.active and c.turn_intent != 'straight' and not c.turned)
    txt(10, H - 20,  f"Cars active : {active:2d}   Waiting to turn : {turning}   Total : {total_spawned}")
    txt(10, H - 40,  f"H-road signal : {_SIG_NAMES[h_sig]}", _SIG_COLORS[h_sig])
    txt(10, H - 60,  f"V-road signal : {_SIG_NAMES[v_sig]}", _SIG_COLORS[v_sig])
    txt(10, H - 80,  f"Green duration : {green_dur} ticks   ( + / - to change )")
    sim_s = "PAUSED" if paused else "RUNNING"
    txt(10, H - 100, f"Simulation : {sim_s}     Mode : {'DAY' if day_mode else 'NIGHT'}")
    txt(10, H - 120, "S=pause  A=add car  N=night  +=more green  -=less  Q=quit")
    txt(10, H - 140, "Yellow dot = turn signal (car will turn at intersection)")

    for i, (sig, label) in enumerate([(h_sig, 'H'), (v_sig, 'V')]):
        glColor3f(*_SIG_COLORS[sig])
        filled_circle(W - 26, H - 20 - i * 38, 13)
        glColor3f(0, 0, 0)
        draw_text(W - 30, H - 15 - i * 38, label)

# ═══════════════════════════════════════════ GLUT callbacks ══════════════════
def display():
    if day_mode:
        glClearColor(0.53, 0.81, 0.92, 1)
    else:
        glClearColor(0.04, 0.04, 0.14, 1)
    glClear(GL_COLOR_BUFFER_BIT)

    draw_road()
    draw_buildings()
    draw_trees()
    draw_street_lamps()

    draw_traffic_light(CX - RW - 22, CY - RW - 128, h_sig)
    draw_traffic_light(CX + RW +  5, CY - RW - 128, v_sig)
    draw_traffic_light(CX - RW - 22, CY + RW +   5, v_sig)
    draw_traffic_light(CX + RW +  5, CY + RW +   5, h_sig)

    for car in cars:
        if car.active:
            car.draw()

    draw_hud()
    glFlush()


def timer_cb(val):
    global frame_no
    if not paused:
        frame_no += 1
        update_signals()

        if frame_no % 100 == 0 and sum(1 for c in cars if c.active) < 16:
            spawn_car()

        for car in cars:
            if car.active:
                car.stopped = should_stop_signal(car) or should_stop_following(car)
                car.move()

        cars[:] = [c for c in cars if c.active]

    glutPostRedisplay()
    glutTimerFunc(16, timer_cb, 0)


def keyboard_cb(key, x, y):
    global paused, day_mode, green_dur
    if isinstance(key, bytes):
        key = key.decode('utf-8', errors='replace')
    k = key.lower()
    if   k == 's': paused    = not paused
    elif k == 'a': spawn_car()
    elif k == 'n': day_mode  = not day_mode
    elif k in ('+', '='): green_dur = min(600, green_dur + 20)
    elif k == '-':         green_dur = max(40,  green_dur - 20)
    elif k == 'q': sys.exit(0)
    glutPostRedisplay()


def init_gl():
    global STOP_LINES
    STOP_LINES = {
        RIGHT: CX - RW - 10,
        LEFT : CX + RW + 10,
        UP   : CY - RW - 10,
        DOWN : CY + RW + 10,
    }
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, W, 0, H)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    for _ in range(6):
        spawn_car()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutInitWindowSize(W, H)
    glutInitWindowPosition(60, 30)
    glutCreateWindow(b"2D Traffic Simulation  |  OpenGL")
    init_gl()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard_cb)
    glutTimerFunc(16, timer_cb, 0)
    glutMainLoop()


if __name__ == '__main__':
    main()
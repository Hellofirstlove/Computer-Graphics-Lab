from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random

# ═══════════════════════════════════════════════════════════
# WINDOW
# ═══════════════════════════════════════════════════════════
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# ═══════════════════════════════════════════════════════════
# GEOMETRY
# ═══════════════════════════════════════════════════════════
HR_Y = -0.10   # horizontal right lane  y-centre
HL_Y = 0.10   # horizontal left  lane  y-centre
VU_X = 0.10   # vertical   up    lane  x-centre
VD_X = -0.10   # vertical   down  lane  x-centre

JX0, JX1 = -0.20, 0.20   # junction box
JY0, JY1 = -0.20, 0.20

SPAWN_DIST = 1.15
DESPAWN_DIST = 1.30

CAR_L = 0.080
CAR_W = 0.040
MIN_GAP = CAR_L + 0.055   # ≈ 0.135

# Stop-line distances (where a car must halt if not green)
STOP_MARGIN = CAR_L * 0.6

# ═══════════════════════════════════════════════════════════
# GLOBALS
# ═══════════════════════════════════════════════════════════
cars = []
simulation_running = True
night_mode = False
vehicle_count = 0

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════


def draw_circle(cx, cy, r, seg=32):
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(cx, cy)
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()


def draw_rect(x0, y0, x1, y1):
    glBegin(GL_QUADS)
    glVertex2f(x0, y0)
    glVertex2f(x1, y0)
    glVertex2f(x1, y1)
    glVertex2f(x0, y1)
    glEnd()


def draw_text(x, y, text):
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))


def car_in_junction(car):
    """True when any part of the car overlaps the junction box."""
    return (JX0 - CAR_L * 0.5 < car.x < JX1 + CAR_L * 0.5 and
            JY0 - CAR_L * 0.5 < car.y < JY1 + CAR_L * 0.5)


def junction_clear():
    """True when NO car is inside or approaching the junction box."""
    return not any(car_in_junction(c) for c in cars)


def count_cars_in_lane(lane):
    return sum(1 for c in cars if c.lane == lane)

# ═══════════════════════════════════════════════════════════
# TRAFFIC SIGNAL  — 4-phase rotation, dynamic green time
# ═══════════════════════════════════════════════════════════
#
# Phase order:  HR_GREEN → HL_GREEN → VU_GREEN → VD_GREEN → repeat
# Between every green phase there is:
#   1. A YELLOW sub-phase  (fixed YELLOW_TICKS)
#   2. A CLEARING sub-phase (both/all red; wait until junction empty)
#
# Green duration = BASE_GREEN + PER_CAR_BONUS * (cars in that lane)
# so heavy traffic gets longer green time, preventing queues from
# causing collisions when the signal finally cycles back.
#
# ═══════════════════════════════════════════════════════════


PHASES = ["HR_GREEN", "HL_GREEN", "VU_GREEN", "VD_GREEN"]
BASE_GREEN = 200   # ticks (~3.3 s at 60 fps) minimum
PER_CAR_BONUS = 40   # extra ticks per car waiting in that lane
YELLOW_TICKS = 55

# Lane that each phase serves
PHASE_LANE = {
    "HR_GREEN": "horizontal_right",
    "HL_GREEN": "horizontal_left",
    "VU_GREEN": "vertical_up",
    "VD_GREEN": "vertical_down",
}


class TrafficSignal:
    """
    4-phase signal:  one lane green at a time.
    Clears junction completely before switching.
    Green duration adapts to queue length.
    """

    def __init__(self):
        self._phase_idx = 0          # index into PHASES
        self._sub = "GREEN"    # "GREEN" | "YELLOW" | "CLEARING"
        self.timer = 0
        self._green_ticks = BASE_GREEN
        self._update_lights()

    # ── public state for cars ───────────────────────────
    def is_green(self, lane):
        return self._active_lane() == lane and self._sub == "GREEN"

    def signal_for_lane(self, lane):
        """Returns 'GREEN', 'YELLOW', or 'RED' for the given lane."""
        if lane == self._active_lane():
            return self._sub if self._sub != "CLEARING" else "RED"
        return "RED"

    # ── internal ────────────────────────────────────────
    def _active_lane(self):
        return PHASE_LANE[PHASES[self._phase_idx]]

    def _update_lights(self):
        """Compute per-direction colours for drawing."""
        al = self._active_lane()
        sub = self._sub
        self._lane_state = {}
        for lane in PHASE_LANE.values():
            if lane == al:
                if sub == "GREEN":
                    self._lane_state[lane] = "GREEN"
                elif sub == "YELLOW":
                    self._lane_state[lane] = "YELLOW"
                else:
                    self._lane_state[lane] = "RED"
            else:
                self._lane_state[lane] = "RED"

    def _lane_colour(self, lane):
        return self._lane_state.get(lane, "RED")

    def update(self):
        self.timer += 1

        if self._sub == "GREEN":
            if self.timer >= self._green_ticks:
                self._sub = "YELLOW"
                self.timer = 0
                self._update_lights()

        elif self._sub == "YELLOW":
            if self.timer >= YELLOW_TICKS:
                self._sub = "CLEARING"
                self.timer = 0
                self._update_lights()

        elif self._sub == "CLEARING":
            if junction_clear():
                # Advance to next phase
                self._phase_idx = (self._phase_idx + 1) % len(PHASES)
                # Compute adaptive green time for the NEXT lane
                next_lane = PHASE_LANE[PHASES[self._phase_idx]]
                queue = count_cars_in_lane(next_lane)
                self._green_ticks = BASE_GREEN + PER_CAR_BONUS * queue
                self._sub = "GREEN"
                self.timer = 0
                self._update_lights()

    # ── drawing ─────────────────────────────────────────
    def draw(self):
        hr = self._lane_colour("horizontal_right")
        hl = self._lane_colour("horizontal_left")
        vu = self._lane_colour("vertical_up")
        vd = self._lane_colour("vertical_down")
        self._draw_signal(-0.32, -0.32, hr)   # SW  → serves horizontal_right
        self._draw_signal(0.22,  0.22, hl)   # NE  → serves horizontal_left
        self._draw_signal(0.22, -0.32, vu)   # SE  → serves vertical_up
        self._draw_signal(-0.32,  0.22, vd)   # NW  → serves vertical_down

    def _draw_signal(self, px, py, state):
        pole_h = 0.20
        bw = 0.040
        bh = 0.11
        rad = 0.014
        glColor3f(0.25, 0.25, 0.25)
        draw_rect(px - 0.009, py, px + 0.009, py + pole_h)
        bx = px - bw / 2
        by = py + pole_h - bh
        glColor3f(0.12, 0.12, 0.12)
        draw_rect(bx, by, bx + bw, by + bh)
        glColor3f(0.38, 0.38, 0.38)
        glLineWidth(1)
        glBegin(GL_LINE_LOOP)
        glVertex2f(bx, by)
        glVertex2f(bx+bw, by)
        glVertex2f(bx+bw, by+bh)
        glVertex2f(bx, by+bh)
        glEnd()
        cx = px
        glColor3f(1.0, 0.10, 0.10) if state == "RED" else glColor3f(
            0.22, 0.04, 0.04)
        draw_circle(cx, by+bh-0.020, rad)
        glColor3f(1.0, 0.85, 0.00) if state == "YELLOW" else glColor3f(
            0.22, 0.20, 0.00)
        draw_circle(cx, by+bh-0.055, rad)
        glColor3f(0.10, 1.00, 0.20) if state == "GREEN" else glColor3f(
            0.03, 0.22, 0.06)
        draw_circle(cx, by+bh-0.090, rad)

    # ── HUD helpers ──────────────────────────────────────
    @property
    def state(self):
        return f"{PHASES[self._phase_idx]}/{self._sub}"

    @property
    def horizontal(self):   # kept for HUD
        hr = self._lane_colour("horizontal_right")
        hl = self._lane_colour("horizontal_left")
        if hr == "GREEN" or hl == "GREEN":
            return "GREEN"
        if hr == "YELLOW" or hl == "YELLOW":
            return "YELLOW"
        return "RED"

    @property
    def vertical(self):
        vu = self._lane_colour("vertical_up")
        vd = self._lane_colour("vertical_down")
        if vu == "GREEN" or vd == "GREEN":
            return "GREEN"
        if vu == "YELLOW" or vd == "YELLOW":
            return "YELLOW"
        return "RED"


signal = TrafficSignal()

# ═══════════════════════════════════════════════════════════
# CAR COLOURS
# ═══════════════════════════════════════════════════════════
CAR_COLORS = [
    (0.85, 0.12, 0.12), (0.12, 0.40, 0.85), (0.10, 0.72, 0.22),
    (0.95, 0.62, 0.08), (0.68, 0.12, 0.80), (0.93, 0.93, 0.93),
    (0.14, 0.14, 0.14), (0.15, 0.72, 0.78),
]

# ═══════════════════════════════════════════════════════════
# CAR
# ═══════════════════════════════════════════════════════════


class Car:
    """
    heading : degrees CCW from east  (east=0 north=90 west=180 south=270)
    committed : True once the car has crossed its stop line into the junction;
                a committed car is NEVER stopped for red lights – it must clear.
    """

    def __init__(self, lane):
        self.lane = lane
        self.speed = 0.0028 + random.uniform(0, 0.0007)
        self.color = random.choice(CAR_COLORS)
        self.turn = random.choice(["straight", "left"])
        self.turning = False
        self.arc_prog = 0.0
        self.committed = False

        if lane == "horizontal_right":
            self.heading = 0.0
            self.x, self.y = -SPAWN_DIST, HR_Y
        elif lane == "horizontal_left":
            self.heading = 180.0
            self.x, self.y = SPAWN_DIST, HL_Y
        elif lane == "vertical_up":
            self.heading = 90.0
            self.x, self.y = VU_X, -SPAWN_DIST
        elif lane == "vertical_down":
            self.heading = 270.0
            self.x, self.y = VD_X,  SPAWN_DIST

    # ── following-distance ────────────────────────────────
    def can_move(self):
        for o in cars:
            if o is self or o.lane != self.lane:
                continue
            if self.lane == "horizontal_right":
                if o.x > self.x and o.x - self.x < MIN_GAP:
                    return False
            elif self.lane == "horizontal_left":
                if o.x < self.x and self.x - o.x < MIN_GAP:
                    return False
            elif self.lane == "vertical_up":
                if o.y > self.y and o.y - self.y < MIN_GAP:
                    return False
            elif self.lane == "vertical_down":
                if o.y < self.y and self.y - o.y < MIN_GAP:
                    return False
        return True

    # ── red-light stop ────────────────────────────────────
    def must_stop(self):
        """
        Stop only when:
          1. Not committed to the junction yet.
          2. Signal is NOT green for this exact lane.
          3. Car has reached its stop line.
          4. The junction is NOT clear (safety: never enter while others are turning).
        """
        if self.committed:
            return False

        lane_sig = signal.signal_for_lane(self.lane)
        if lane_sig == "GREEN":
            # Even on green, wait if a turning car is still in the box
            if not junction_clear() and not car_in_junction(self):
                return True
            return False

        # On red or yellow: stop at stop line
        if self.lane == "horizontal_right":
            return self.x >= JX0 - STOP_MARGIN
        elif self.lane == "horizontal_left":
            return self.x <= JX1 + STOP_MARGIN
        elif self.lane == "vertical_up":
            return self.y >= JY0 - STOP_MARGIN
        elif self.lane == "vertical_down":
            return self.y <= JY1 + STOP_MARGIN
        return False

    # ── move ──────────────────────────────────────────────
    def move(self):
        global vehicle_count

        # Mark committed once inside junction box
        if not self.committed and car_in_junction(self):
            self.committed = True

        if not self.can_move():
            return
        if self.must_stop():
            return

        if self.turning:
            self._do_arc()
        else:
            # Trigger left turn at junction centre
            if self.turn == "left":
                if self.lane == "horizontal_right" and self.x >= -0.05:
                    self._start_arc()
                elif self.lane == "horizontal_left" and self.x <= 0.05:
                    self._start_arc()
                elif self.lane == "vertical_up" and self.y >= -0.05:
                    self._start_arc()
                elif self.lane == "vertical_down" and self.y <= 0.05:
                    self._start_arc()
            if not self.turning:
                h = math.radians(self.heading)
                self.x += self.speed * math.cos(h)
                self.y += self.speed * math.sin(h)

        # Despawn / respawn
        if (self.x > DESPAWN_DIST or self.x < -DESPAWN_DIST or
                self.y > DESPAWN_DIST or self.y < -DESPAWN_DIST):
            vehicle_count += 1
            self.__init__(self.lane)

    def _start_arc(self):
        self.turning = True
        self.arc_prog = 0.0
        self.turn_radius = 0.12
        left = math.radians(self.heading + 90.0)
        self.arc_cx = self.x + self.turn_radius * math.cos(left)
        self.arc_cy = self.y + self.turn_radius * math.sin(left)
        self.arc_start = self.heading - 90.0

    def _do_arc(self):
        self.arc_prog += 1.0
        cur = math.radians(self.arc_start + self.arc_prog)
        self.x = self.arc_cx + self.turn_radius * math.cos(cur)
        self.y = self.arc_cy + self.turn_radius * math.sin(cur)
        self.heading = (self.arc_start + self.arc_prog + 90.0) % 360.0

        if self.arc_prog >= 90.0:
            self.heading = round((self.arc_start + 180.0) % 360.0)
            h = int(self.heading) % 360
            if h == 0:
                self.lane = "horizontal_right"
            elif h == 90:
                self.lane = "vertical_up"
            elif h == 180:
                self.lane = "horizontal_left"
            elif h == 270:
                self.lane = "vertical_down"
            self.turning = False
            self.turn = "done"
            self.committed = False   # may face a new stop line on exit

    # ── draw ──────────────────────────────────────────────
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, 0.0)
        glRotatef(self.heading, 0.0, 0.0, 1.0)
        self._draw_local()
        glPopMatrix()

    def _draw_local(self):
        L, W = CAR_L, CAR_W
        r, g, b = self.color
        hl, hw = L / 2.0, W / 2.0

        glColor3f(r, g, b)
        draw_rect(-hl, -hw, hl, hw)

        glColor3f(r*0.68, g*0.68, b*0.68)
        draw_rect(hl*0.40, -hw+0.003, hl, hw-0.003)

        rr = min(1.0, r*1.12+0.08)
        rg = min(1.0, g*1.12+0.08)
        rb = min(1.0, b*1.12+0.08)
        glColor3f(rr, rg, rb)
        rx0, rx1 = -hl*0.30, hl*0.42
        ry0, ry1 = -hw*0.78, hw*0.78
        draw_rect(rx0, ry0, rx1, ry1)

        glColor3f(0.44, 0.71, 0.94)
        mg = 0.003
        draw_rect(rx0+mg, ry0+mg, rx1-mg, ry1-mg)

        glColor3f(rr*0.50, rg*0.50, rb*0.50)
        glLineWidth(2)
        glBegin(GL_LINES)
        glVertex2f((rx0+rx1)/2, ry0+mg)
        glVertex2f((rx0+rx1)/2, ry1-mg)
        glEnd()

        glColor3f(1.0, 0.97, 0.68)
        draw_circle(hl-0.005, -hw*0.52, 0.007)
        draw_circle(hl-0.005,  hw*0.52, 0.007)

        glColor3f(0.90, 0.05, 0.05)
        draw_circle(-hl+0.005, -hw*0.52, 0.006)
        draw_circle(-hl+0.005,  hw*0.52, 0.006)

        ax, wr = hl*0.66, 0.009
        glColor3f(0.10, 0.10, 0.10)
        for sx in (-ax, ax):
            for sy in (-hw-wr, hw+wr):
                draw_circle(sx, sy, wr)
        glColor3f(0.38, 0.38, 0.38)
        for sx in (-ax, ax):
            for sy in (-hw-wr, hw+wr):
                draw_circle(sx, sy, wr*0.42)

# ═══════════════════════════════════════════════════════════
# SPAWN  —  only when signal is green for that exact lane
# ═══════════════════════════════════════════════════════════


def spawn_car(lane):
    SAFE_R = 0.30
    if lane == "horizontal_right":
        sx, sy = -SPAWN_DIST, HR_Y
    elif lane == "horizontal_left":
        sx, sy = SPAWN_DIST, HL_Y
    elif lane == "vertical_up":
        sx, sy = VU_X, -SPAWN_DIST
    elif lane == "vertical_down":
        sx, sy = VD_X,  SPAWN_DIST
    else:
        return

    # Don't require green to queue — cars can spawn and wait at red
    for car in cars:
        if car.lane != lane:
            continue
        if math.hypot(car.x - sx, car.y - sy) < SAFE_R:
            return

    new_car = Car(lane)
    cars.append(new_car)

    # Re-compute green extension for the active lane
    _extend_green_for_queue()


def _extend_green_for_queue():
    """After any spawn, recalculate green ticks for the CURRENT active lane."""
    active_lane = PHASE_LANE[PHASES[signal._phase_idx]]
    queue = count_cars_in_lane(active_lane)
    signal._green_ticks = BASE_GREEN + PER_CAR_BONUS * queue

# ═══════════════════════════════════════════════════════════
# ROADS
# ═══════════════════════════════════════════════════════════


def draw_jersey_barrier_h(x0, x1, cy, skip_x0=-9, skip_x1=-9):
    seg, gap, BH = 0.11, 0.010, 0.034
    cur = x0
    while cur < x1:
        se = min(cur + seg, x1)
        if cur >= skip_x0 and se <= skip_x1:
            cur += seg + gap
            continue
        if cur < skip_x0 and se > skip_x0:
            se = skip_x0
        if cur < skip_x1 and se > skip_x1:
            cur = skip_x1
            continue
        sx0, sx1 = cur, se
        glColor3f(0.48, 0.48, 0.48)
        draw_rect(sx0, cy-BH, sx1, cy-BH*0.50)
        glColor3f(0.70, 0.70, 0.70)
        draw_rect(sx0+0.004, cy-BH*0.50, sx1-0.004, cy+BH*0.50)
        glColor3f(0.86, 0.86, 0.86)
        draw_rect(sx0+0.008, cy+BH*0.50, sx1-0.008, cy+BH)
        glColor3f(0.88, 0.76, 0.08)
        draw_rect(sx0+0.004, cy-0.005, sx1-0.004, cy+0.005)
        glColor3f(1.0, 1.0, 1.0)
        glLineWidth(1)
        glBegin(GL_LINES)
        glVertex2f(sx0+0.008, cy+BH-0.001)
        glVertex2f(sx1-0.008, cy+BH-0.001)
        glEnd()
        cur += seg + gap


def draw_jersey_barrier_v(y0, y1, cx, skip_y0=-9, skip_y1=-9):
    seg, gap, BW = 0.11, 0.010, 0.034
    cur = y0
    while cur < y1:
        se = min(cur + seg, y1)
        if cur >= skip_y0 and se <= skip_y1:
            cur += seg + gap
            continue
        if cur < skip_y0 and se > skip_y0:
            se = skip_y0
        if cur < skip_y1 and se > skip_y1:
            cur = skip_y1
            continue
        sy0, sy1 = cur, se
        glColor3f(0.48, 0.48, 0.48)
        draw_rect(cx-BW, sy0, cx-BW*0.50, sy1)
        glColor3f(0.70, 0.70, 0.70)
        draw_rect(cx-BW*0.50, sy0+0.004, cx+BW*0.50, sy1-0.004)
        glColor3f(0.86, 0.86, 0.86)
        draw_rect(cx+BW*0.50, sy0+0.008, cx+BW, sy1-0.008)
        glColor3f(0.88, 0.76, 0.08)
        draw_rect(cx-0.005, sy0+0.004, cx+0.005, sy1-0.004)
        glColor3f(1.0, 1.0, 1.0)
        glLineWidth(1)
        glBegin(GL_LINES)
        glVertex2f(cx+BW-0.001, sy0+0.008)
        glVertex2f(cx+BW-0.001, sy1-0.008)
        glEnd()
        cur += seg + gap


def draw_roads():
    glColor3f(0.22, 0.22, 0.22)
    draw_rect(-1.0, -0.20,  1.0,  0.20)
    draw_rect(-0.20, -1.0,  0.20,  1.0)

    glColor3f(0.88, 0.88, 0.88)
    glLineWidth(2)
    glBegin(GL_LINES)
    for ex in ((-1.0, -0.20), (0.20, 1.0)):
        glVertex2f(ex[0], -0.20)
        glVertex2f(ex[1], -0.20)
        glVertex2f(ex[0],  0.20)
        glVertex2f(ex[1],  0.20)
    for ey in ((-1.0, -0.20), (0.20, 1.0)):
        glVertex2f(-0.20, ey[0])
        glVertex2f(-0.20, ey[1])
        glVertex2f(0.20, ey[0])
        glVertex2f(0.20, ey[1])
    glEnd()

    glColor3f(1, 1, 1)
    glLineWidth(2)
    glBegin(GL_LINES)
    for i in range(-10, 11):
        bx = i * 0.10
        if JX0 < bx < JX1:
            continue
        for ly in (-0.05, 0.05):
            glVertex2f(bx+0.01, ly)
            glVertex2f(bx+0.06, ly)
        by = bx
        if JY0 < by < JY1:
            continue
        for lx in (-0.05, 0.05):
            glVertex2f(lx, by+0.01)
            glVertex2f(lx, by+0.06)
    glEnd()

    glColor3f(0.88, 0.74, 0.0)
    glLineWidth(1)
    glBegin(GL_LINES)
    for i in range(5):
        t = JX0 + i * 0.10
        glVertex2f(JX0, t)
        glVertex2f(JX1, t)
        glVertex2f(t, JY0)
        glVertex2f(t, JY1)
    glEnd()

    draw_jersey_barrier_h(-1.0, 1.0, 0.0, skip_x0=JX0, skip_x1=JX1)
    draw_jersey_barrier_v(-1.0, 1.0, 0.0, skip_y0=JY0, skip_y1=JY1)

# ═══════════════════════════════════════════════════════════
# SKY / BACKGROUND
# ═══════════════════════════════════════════════════════════


def draw_sky():
    if night_mode:
        glColor3f(1.0, 1.0, 0.90)
        draw_circle(0.80, 0.80, 0.07)
        glColor3f(0.02, 0.02, 0.08)
        draw_circle(0.84, 0.83, 0.06)
        random.seed(42)
        glColor3f(1, 1, 1)
        for _ in range(30):
            sx = random.uniform(-0.95, 0.95)
            sy = random.uniform(0.30, 0.95)
            if 0.55 < sx < 0.95 and 0.55 < sy < 0.95:
                continue
            draw_circle(sx, sy, 0.004)
    else:
        glColor3f(1.0, 0.95, 0.18)
        draw_circle(0.80, 0.80, 0.085)
        glColor3f(1.0, 0.85, 0.10)
        glLineWidth(2)
        glBegin(GL_LINES)
        for i in range(8):
            a = math.radians(i * 45)
            glVertex2f(0.80+0.105*math.cos(a), 0.80+0.105*math.sin(a))
            glVertex2f(0.80+0.165*math.cos(a), 0.80+0.165*math.sin(a))
        glEnd()


def background():
    if night_mode:
        glClearColor(0.02, 0.02, 0.10, 1)
    else:
        glClearColor(0.44, 0.77, 0.97, 1)

# ═══════════════════════════════════════════════════════════
# DISPLAY
# ═══════════════════════════════════════════════════════════


def display():
    background()
    glClear(GL_COLOR_BUFFER_BIT)
    draw_sky()
    draw_roads()
    signal.draw()
    for car in cars:
        car.draw()

    # HUD
    glColor3f(0.05, 0.05, 0.05)
    active_lane = PHASE_LANE[PHASES[signal._phase_idx]]
    draw_text(-0.95,  0.92, f"Vehicles Passed: {vehicle_count}")
    draw_text(-0.95,  0.85, f"Cars Active: {len(cars)}")
    draw_text(-0.95,  0.78, f"Phase: {signal.state}")
    draw_text(-0.95,  0.71,
              f"Green lane: {active_lane}  ticks: {signal._green_ticks}")
    draw_text(-0.95,  0.64,
              "1-HR  2-HL  3-VU  4-VD  p=pause  s=start  n=night  r=reset")
    glutSwapBuffers()

# ═══════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════


def update(value):
    if simulation_running:
        signal.update()
        for car in cars:
            car.move()
    glutPostRedisplay()
    glutTimerFunc(16, update, 0)

# ═══════════════════════════════════════════════════════════
# KEYBOARD
# ═══════════════════════════════════════════════════════════


def keyboard(key, x, y):
    global simulation_running, night_mode
    key = key.decode("utf-8")
    if key == 's':
        simulation_running = True
    elif key == 'p':
        simulation_running = False
    elif key == '1':
        spawn_car("horizontal_right")
    elif key == '2':
        spawn_car("horizontal_left")
    elif key == '3':
        spawn_car("vertical_up")
    elif key == '4':
        spawn_car("vertical_down")
    elif key == 'n':
        night_mode = not night_mode
    elif key == 'r':
        cars.clear()

# ═══════════════════════════════════════════════════════════
# INIT / MAIN
# ═══════════════════════════════════════════════════════════


def init():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(-1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"Traffic Simulation - 4-Phase Signal")
    init()
    # Spawn initial cars in the first active lane only
    spawn_car("horizontal_right")
    spawn_car("horizontal_right")
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(16, update, 0)
    glutMainLoop()


main()

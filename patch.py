
import re

with open("testmid.py", "r") as f:
    code = f.read()

# 1) Replace LATERAL_SPEED with turn constants
old = 'LATERAL_SPEED = 1.4   # px per tick for lane-change glide'
new = """# Turn mappings and geometry
TURN_MAP = {
    (RIGHT, 'left'): UP,    (RIGHT, 'right'): DOWN,
    (LEFT,  'left'): DOWN,  (LEFT,  'right'): UP,
    (UP,    'left'): LEFT,  (UP,    'right'): RIGHT,
    (DOWN,  'left'): RIGHT, (DOWN,  'right'): LEFT,
}
ENTRY_LANE = {
    RIGHT: ('y', CY - RW // 4), LEFT: ('y', CY + RW // 4),
    UP:    ('x', CX + RW // 4), DOWN: ('x', CX - RW // 4),
}
DIR_ANGLE = {RIGHT: 0, UP: 90, LEFT: 180, DOWN: 270}
RIGHT_VEC = {RIGHT: (0,-1), LEFT: (0,1), UP: (1,0), DOWN: (-1,0)}
LEFT_VEC  = {RIGHT: (0,1), LEFT: (0,-1), UP: (-1,0), DOWN: (1,0)}
TURN_RADIUS = RW // 2
TURN_SPEED  = 0.025"""
code = code.replace(old, new)

# 2) Replace lane-change state in __init__
old = """        # \u2500\u2500 Lane-change state \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        self.lane           = 0                         # 0=inner, 1=outer
        self.target_lateral = float(LANES[direction][0])# world coord target
        self.lateral        = self.target_lateral       # current world coord
        self.lc_timer       = random.randint(180, 400)  # ticks until next check
        self.changing_lane  = False"""
new = """        # \u2500\u2500 Turn state \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        self.lane        = 0
        self.turn_intent = random.choice(['straight']*5 + ['left', 'right'])
        self.turned      = False
        self.turning     = False
        self.turn_progress = 0.0
        self.turn_cx = self.turn_cy = 0.0
        self.turn_a0 = self.turn_a1 = 0.0
        self.heading  = float(DIR_ANGLE[direction])"""
code = code.replace(old, new)

# 3) Replace try_lane_change + update_lateral with turn logic
old_start = "    # \u2500\u2500 Lane-change logic"
old_end = "            self.x = self.lateral"
i0 = code.index(old_start)
i1 = code.index(old_end) + len(old_end)
new_turn = """    # \u2500\u2500 Turn logic \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    def check_turn(self):
        import math as _m
        if self.turn_intent == 'straight' or self.turned or self.turning:
            return
        in_box = (CX - RW < self.x < CX + RW and CY - RW < self.y < CY + RW)
        if not in_box:
            return
        ok = False
        if   self.dir == RIGHT and self.x >= CX - RW // 3: ok = True
        elif self.dir == LEFT  and self.x <= CX + RW // 3: ok = True
        elif self.dir == UP    and self.y >= CY - RW // 3: ok = True
        elif self.dir == DOWN  and self.y <= CY + RW // 3: ok = True
        if not ok:
            return
        new_dir = TURN_MAP[(self.dir, self.turn_intent)]
        axis, lane_pos = ENTRY_LANE[new_dir]
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
        if self.turn_intent == 'left':
            opp = {RIGHT: LEFT, LEFT: RIGHT, UP: DOWN, DOWN: UP}
            for ot in cars:
                if ot is self or not ot.active or ot.dir != opp[self.dir]:
                    continue
                if abs(ot.x - self.x) < SAFE_GAP and abs(ot.y - self.y) < SAFE_GAP:
                    return
        R = TURN_RADIUS
        if self.turn_intent == 'right':
            rv = RIGHT_VEC[self.dir]
            self.turn_cx = self.x + R * rv[0]
            self.turn_cy = self.y + R * rv[1]
        else:
            lv = LEFT_VEC[self.dir]
            self.turn_cx = self.x + R * lv[0]
            self.turn_cy = self.y + R * lv[1]
        self.turn_a0 = _m.degrees(_m.atan2(self.y - self.turn_cy, self.x - self.turn_cx))
        if self.turn_intent == 'right':
            self.turn_a1 = self.turn_a0 - 90
        else:
            self.turn_a1 = self.turn_a0 + 90
        self.turning = True
        self.turn_progress = 0.0
        self.turn_new_dir = new_dir

    def update_turn(self):
        import math as _m
        if not self.turning:
            return
        self.turn_progress += TURN_SPEED
        if self.turn_progress >= 1.0:
            self.turn_progress = 1.0
            a = _m.radians(self.turn_a1)
            self.x = self.turn_cx + TURN_RADIUS * _m.cos(a)
            self.y = self.turn_cy + TURN_RADIUS * _m.sin(a)
            self.dir = self.turn_new_dir
            self.heading = float(DIR_ANGLE[self.dir])
            self.turned = True
            self.turning = False
            return
        t = self.turn_progress
        smooth_t = t * t * (3 - 2 * t)
        cur_a = _m.radians(self.turn_a0 + (self.turn_a1 - self.turn_a0) * smooth_t)
        self.x = self.turn_cx + TURN_RADIUS * _m.cos(cur_a)
        self.y = self.turn_cy + TURN_RADIUS * _m.sin(cur_a)
        self.heading = self.turn_a0 + (self.turn_a1 - self.turn_a0) * smooth_t - 90 if self.turn_intent == 'right' else self.turn_a0 + (self.turn_a1 - self.turn_a0) * smooth_t + 90
        start_h = DIR_ANGLE[self.dir]
        end_h = DIR_ANGLE[self.turn_new_dir]
        diff = end_h - start_h
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        self.heading = start_h + diff * smooth_t"""
code = code[:i0] + new_turn + code[i1:]

# 4) Replace move method
old = """    def move(self):
        if not self.active:
            return

        # Lane-change decision (every car, every tick countdown)
        self.try_lane_change()

        # Smooth lateral glide toward target lane
        self.update_lateral()

        # Forward movement (blocked when stopped)
        if not self.stopped:
            if   self.dir == RIGHT: self.x += self.spd
            elif self.dir == LEFT:  self.x -= self.spd
            elif self.dir == UP:    self.y += self.spd
            else:                   self.y -= self.spd

        margin = 90
        if (self.x < -margin or self.x > W + margin or
                self.y < -margin or self.y > H + margin):
            self.active = False"""
new = """    def move(self):
        if not self.active:
            return
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
            self.active = False"""
code = code.replace(old, new)

# 5) Replace draw rotation with heading-based rotation
old = """        if self.dir in (UP, DOWN):
            glRotatef(90, 0, 0, 1)
        if self.dir in (LEFT, DOWN):
            glScalef(-1, 1, 1)"""
new = """        glRotatef(self.heading, 0, 0, 1)"""
code = code.replace(old, new)

# 6) Replace lane-change indicator with turn signal
old = """        # Lane-change indicator: draw a small white arrow on roof while gliding
        if self.changing_lane:
            glColor3f(1.0, 1.0, 1.0)
            filled_circle(0, 0, 3, 6)"""
new = """        # Turn signal indicator
        if self.turn_intent == 'left' and not self.turned:
            glColor3f(1.0, 0.8, 0.0)
            filled_circle(-3, hh - 2, 3, 6)
        elif self.turn_intent == 'right' and not self.turned:
            glColor3f(1.0, 0.8, 0.0)
            filled_circle(-3, -hh + 2, 3, 6)"""
code = code.replace(old, new)

# 7) Replace HUD
old = """    active = sum(1 for c in cars if c.active)
    changing = sum(1 for c in cars if c.active and c.changing_lane)
    txt(10, H - 20,  f"Cars active : {active:2d}   Changing lane : {changing}   Total : {total_spawned}")"""
new = """    active = sum(1 for c in cars if c.active)
    turning = sum(1 for c in cars if c.active and c.turning)
    txt(10, H - 20,  f"Cars active : {active:2d}   Turning : {turning}   Total : {total_spawned}")"""
code = code.replace(old, new)

old = '    txt(10, H - 140, "White dot on car roof = currently changing lane")'
new = '    txt(10, H - 140, "Yellow dot = turn signal (car will turn at intersection)")'
code = code.replace(old, new)

with open("testmid.py", "w") as f:
    f.write(code)

print("Patched successfully!")

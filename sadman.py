from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import random
import math

# =====================================================
# WINDOW
# =====================================================

WIN_W = 1000
WIN_H = 800

# =====================================================
# ROAD AREA
# =====================================================

ROAD_LEFT = 420
ROAD_RIGHT = 580
ROAD_BOTTOM = 320
ROAD_TOP = 480

# =====================================================
# RIGHT SIDE LANES
# =====================================================

LANE_EAST = 360
LANE_WEST = 440
LANE_NORTH = 540
LANE_SOUTH = 460

# =====================================================
# YELLOW STOP LINES
# =====================================================

LINE_E = ROAD_LEFT - 18
LINE_W = ROAD_RIGHT + 18
LINE_N = ROAD_BOTTOM - 18
LINE_S = ROAD_TOP + 18

# Cars stop slightly before yellow line
STOP_BACK = 28

STOP_E = LINE_E - STOP_BACK
STOP_W = LINE_W + STOP_BACK
STOP_N = LINE_N - STOP_BACK
STOP_S = LINE_S + STOP_BACK

# Same small gap everywhere
MIN_GAP = 48

# Maximum cars from one road
MAX_CARS_PER_ROAD = 7

# =====================================================
# DIRECTIONS
# =====================================================

DIR_EAST = 0
DIR_NORTH = 1
DIR_WEST = 2
DIR_SOUTH = 3

# =====================================================
# TURN TYPES
# =====================================================

TURN_LEFT = -1
TURN_STRAIGHT = 0
TURN_RIGHT = 1

# =====================================================
# LIGHT TYPES
# =====================================================

LIGHT_RED = 0
LIGHT_YELLOW = 1
LIGHT_GREEN = 2

# =====================================================
# SIGNAL PHASES
# =====================================================

PHASE_E_GREEN = 0
PHASE_E_YELLOW = 1
PHASE_N_YELLOW = 2
PHASE_N_GREEN = 3

PHASE_N_END_YELLOW = 4
PHASE_W_YELLOW = 5
PHASE_W_GREEN = 6

PHASE_W_END_YELLOW = 7
PHASE_S_YELLOW = 8
PHASE_S_GREEN = 9

PHASE_S_END_YELLOW = 10
PHASE_E_START_YELLOW = 11

# =====================================================
# GLOBAL VARIABLES
# =====================================================

cars = []

curPhase = PHASE_E_GREEN
phaseTimer = 0

greenTime = 5000
yellowTime = 1200

running = True
nightMode = False

carsPassed = 0
totalSpawned = 0

spawnTimer = 0
SPAWN_INTERVAL = 1800
MAX_CARS = 28

# Used for balanced spawning
spawnCursor = 0


# =====================================================
# BASIC DRAWING FUNCTIONS
# =====================================================

def draw_rect(x1, y1, x2, y2):
    glBegin(GL_QUADS)
    glVertex2f(x1, y1)
    glVertex2f(x2, y1)
    glVertex2f(x2, y2)
    glVertex2f(x1, y2)
    glEnd()


def draw_circle(cx, cy, r, segs=24):
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(cx, cy)

    for i in range(segs + 1):
        a = 2 * math.pi * i / segs
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))

    glEnd()


def draw_text(x, y, text):
    glRasterPos2f(x, y)

    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))


# =====================================================
# MATH HELPERS
# =====================================================

def distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def angle_to_point(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


# =====================================================
# PATH SYSTEM
# Cars follow right-side lane and go outside screen
# =====================================================

def create_path(direction, turn):

    if direction == DIR_EAST:

        if turn == TURN_STRAIGHT:
            return [(-80, LANE_EAST), (STOP_E, LANE_EAST), (WIN_W + 180, LANE_EAST)]

        elif turn == TURN_RIGHT:
            return [(-80, LANE_EAST), (STOP_E, LANE_EAST),
                    (LANE_SOUTH, LANE_EAST), (LANE_SOUTH, -180)]

        else:
            return [(-80, LANE_EAST), (STOP_E, LANE_EAST),
                    (LANE_NORTH, LANE_EAST), (LANE_NORTH, WIN_H + 180)]

    elif direction == DIR_NORTH:

        if turn == TURN_STRAIGHT:
            return [(LANE_NORTH, -80), (LANE_NORTH, STOP_N), (LANE_NORTH, WIN_H + 180)]

        elif turn == TURN_RIGHT:
            return [(LANE_NORTH, -80), (LANE_NORTH, STOP_N),
                    (LANE_NORTH, LANE_EAST), (WIN_W + 180, LANE_EAST)]

        else:
            return [(LANE_NORTH, -80), (LANE_NORTH, STOP_N),
                    (LANE_NORTH, LANE_WEST), (-180, LANE_WEST)]

    elif direction == DIR_WEST:

        if turn == TURN_STRAIGHT:
            return [(WIN_W + 80, LANE_WEST), (STOP_W, LANE_WEST), (-180, LANE_WEST)]

        elif turn == TURN_RIGHT:
            return [(WIN_W + 80, LANE_WEST), (STOP_W, LANE_WEST),
                    (LANE_NORTH, LANE_WEST), (LANE_NORTH, WIN_H + 180)]

        else:
            return [(WIN_W + 80, LANE_WEST), (STOP_W, LANE_WEST),
                    (LANE_SOUTH, LANE_WEST), (LANE_SOUTH, -180)]

    else:

        if turn == TURN_STRAIGHT:
            return [(LANE_SOUTH, WIN_H + 80), (LANE_SOUTH, STOP_S), (LANE_SOUTH, -180)]

        elif turn == TURN_RIGHT:
            return [(LANE_SOUTH, WIN_H + 80), (LANE_SOUTH, STOP_S),
                    (LANE_SOUTH, LANE_WEST), (-180, LANE_WEST)]

        else:
            return [(LANE_SOUTH, WIN_H + 80), (LANE_SOUTH, STOP_S),
                    (LANE_SOUTH, LANE_EAST), (WIN_W + 180, LANE_EAST)]


# =====================================================
# CAR CLASS
# =====================================================

class Car:
    def __init__(self, direction):
        self.startDir = direction

        self.turn = random.choice([
            TURN_STRAIGHT,
            TURN_STRAIGHT,
            TURN_LEFT,
            TURN_RIGHT
        ])

        self.path = create_path(direction, self.turn)

        self.x, self.y = self.path[0]
        self.targetIndex = 1

        self.speed = random.uniform(1.8, 2.5)
        self.curSpeed = self.speed

        self.length = 36
        self.width = 20

        self.counted = False

        tx, ty = self.path[self.targetIndex]
        self.angle = angle_to_point(self.x, self.y, tx, ty)

        self.r = random.uniform(0.3, 1.0)
        self.g = random.uniform(0.3, 1.0)
        self.b = random.uniform(0.3, 1.0)


# =====================================================
# BACKGROUND
# =====================================================

def draw_background():
    if nightMode:
        glColor3f(0.05, 0.07, 0.15)
    else:
        glColor3f(0.55, 0.78, 0.50)

    draw_rect(0, 0, WIN_W, WIN_H)

    if nightMode:
        glColor3f(1, 1, 1)
        random.seed(42)

        for i in range(70):
            draw_circle(random.randint(0, WIN_W), random.randint(0, WIN_H), 1.2, 6)


# =====================================================
# FOOTPATH
# =====================================================

def draw_footpaths():
    glColor3f(0.62, 0.62, 0.62)

    draw_rect(0, ROAD_TOP, WIN_W, ROAD_TOP + 22)
    draw_rect(0, ROAD_BOTTOM - 22, WIN_W, ROAD_BOTTOM)

    draw_rect(ROAD_LEFT - 22, 0, ROAD_LEFT, WIN_H)
    draw_rect(ROAD_RIGHT, 0, ROAD_RIGHT + 22, WIN_H)

    glColor3f(0.85, 0.85, 0.85)

    draw_rect(0, ROAD_TOP + 20, WIN_W, ROAD_TOP + 22)
    draw_rect(0, ROAD_BOTTOM - 22, WIN_W, ROAD_BOTTOM - 20)
    draw_rect(ROAD_LEFT - 22, 0, ROAD_LEFT - 20, WIN_H)
    draw_rect(ROAD_RIGHT + 20, 0, ROAD_RIGHT + 22, WIN_H)


# =====================================================
# BUILDINGS
# =====================================================

def draw_building(x, y, w, h, r, g, b):
    glColor3f(r, g, b)
    draw_rect(x, y, x + w, y + h)

    if nightMode:
        glColor3f(1.0, 0.9, 0.4)
    else:
        glColor3f(0.4, 0.5, 0.6)

    wy = y + 15

    while wy < y + h - 15:
        wx = x + 10

        while wx < x + w - 10:
            draw_rect(wx, wy, wx + 12, wy + 14)
            wx += 25

        wy += 25


def draw_buildings():
    draw_building(60, 560, 90, 150, 0.55, 0.45, 0.40)
    draw_building(170, 540, 100, 180, 0.50, 0.50, 0.55)
    draw_building(290, 560, 90, 150, 0.55, 0.50, 0.45)

    draw_building(720, 540, 130, 190, 0.55, 0.45, 0.40)
    draw_building(870, 570, 90, 150, 0.50, 0.50, 0.55)
    draw_building(620, 570, 80, 120, 0.45, 0.55, 0.60)

    draw_building(60, 60, 120, 210, 0.55, 0.45, 0.40)
    draw_building(200, 80, 100, 160, 0.50, 0.50, 0.55)
    draw_building(320, 70, 80, 130, 0.45, 0.52, 0.58)

    draw_building(720, 70, 130, 180, 0.50, 0.50, 0.55)
    draw_building(870, 70, 90, 150, 0.55, 0.45, 0.40)
    draw_building(620, 80, 80, 130, 0.55, 0.50, 0.45)


# =====================================================
# ROAD AND STOP LINE DRAWING
# =====================================================

def draw_roads():
    glColor3f(0.18, 0.18, 0.18)

    draw_rect(0, ROAD_BOTTOM, WIN_W, ROAD_TOP)
    draw_rect(ROAD_LEFT, 0, ROAD_RIGHT, WIN_H)

    glColor3f(1, 1, 1)

    x = 0
    while x < WIN_W:
        if not (x + 25 > ROAD_LEFT and x < ROAD_RIGHT):
            draw_rect(x, 398, x + 25, 402)
        x += 40

    y = 0
    while y < WIN_H:
        if not (y + 25 > ROAD_BOTTOM and y < ROAD_TOP):
            draw_rect(498, y, 502, y + 25)
        y += 40

    draw_stop_lines()


def draw_stop_lines():
    glColor3f(1, 1, 0)

    draw_rect(LINE_E - 3, ROAD_BOTTOM, LINE_E + 3, 400)
    draw_rect(LINE_W - 3, 400, LINE_W + 3, ROAD_TOP)
    draw_rect(500, LINE_N - 3, ROAD_RIGHT, LINE_N + 3)
    draw_rect(ROAD_LEFT, LINE_S - 3, 500, LINE_S + 3)


# =====================================================
# SIGNAL LOGIC
# =====================================================

def light_for(direction):

    if direction == DIR_EAST:
        if curPhase == PHASE_E_GREEN:
            return LIGHT_GREEN
        if curPhase in [PHASE_E_YELLOW, PHASE_E_START_YELLOW]:
            return LIGHT_YELLOW

    elif direction == DIR_NORTH:
        if curPhase == PHASE_N_GREEN:
            return LIGHT_GREEN
        if curPhase in [PHASE_N_YELLOW, PHASE_N_END_YELLOW]:
            return LIGHT_YELLOW

    elif direction == DIR_WEST:
        if curPhase == PHASE_W_GREEN:
            return LIGHT_GREEN
        if curPhase in [PHASE_W_YELLOW, PHASE_W_END_YELLOW]:
            return LIGHT_YELLOW

    elif direction == DIR_SOUTH:
        if curPhase == PHASE_S_GREEN:
            return LIGHT_GREEN
        if curPhase in [PHASE_S_YELLOW, PHASE_S_END_YELLOW]:
            return LIGHT_YELLOW

    return LIGHT_RED


def signal_allows(direction):
    return light_for(direction) == LIGHT_GREEN


def phase_duration():
    if curPhase in [PHASE_E_GREEN, PHASE_N_GREEN, PHASE_W_GREEN, PHASE_S_GREEN]:
        return greenTime

    return yellowTime


def update_signals(dt):
    global phaseTimer, curPhase

    phaseTimer += dt

    if phaseTimer >= phase_duration():
        phaseTimer = 0
        curPhase = (curPhase + 1) % 12


# =====================================================
# SIGNAL DRAWING
# =====================================================

def draw_signal_box(cx, cy, active):
    glColor3f(0.2, 0.2, 0.2)
    draw_rect(cx - 2, cy - 30, cx + 2, cy)

    glColor3f(0.12, 0.12, 0.12)
    draw_rect(cx - 14, cy, cx + 14, cy + 70)

    glColor3f(1 if active == LIGHT_RED else 0.3, 0.05, 0.05)
    draw_circle(cx, cy + 56, 8)

    glColor3f(
        1 if active == LIGHT_YELLOW else 0.3,
        0.85 if active == LIGHT_YELLOW else 0.25,
        0.05
    )
    draw_circle(cx, cy + 35, 8)

    glColor3f(
        0.05,
        1 if active == LIGHT_GREEN else 0.3,
        0.1
    )
    draw_circle(cx, cy + 14, 8)


def draw_signals():
    draw_signal_box(ROAD_LEFT - 55, ROAD_BOTTOM - 100, light_for(DIR_EAST))
    draw_signal_box(ROAD_RIGHT + 55, ROAD_BOTTOM - 100, light_for(DIR_NORTH))
    draw_signal_box(ROAD_RIGHT + 55, ROAD_TOP + 35, light_for(DIR_WEST))
    draw_signal_box(ROAD_LEFT - 55, ROAD_TOP + 35, light_for(DIR_SOUTH))


# =====================================================
# CAR DRAWING
# =====================================================

def draw_car(c):
    w = c.length
    h = c.width

    glPushMatrix()

    glTranslatef(c.x, c.y, 0)
    glRotatef(math.degrees(c.angle), 0, 0, 1)

    glColor3f(c.r, c.g, c.b)
    draw_rect(-w / 2, -h / 2, w / 2, h / 2)

    glColor3f(c.r * 0.65, c.g * 0.65, c.b * 0.65)
    draw_rect(-w / 2 + 8, -h / 2 + 3, w / 2 - 12, h / 2 - 3)

    glColor3f(0.55, 0.75, 0.95)
    draw_rect(w / 2 - 12, -h / 2 + 4, w / 2 - 4, h / 2 - 4)

    glColor3f(0.05, 0.05, 0.05)
    draw_circle(-w / 2 + 8, -h / 2 - 1, 4)
    draw_circle(w / 2 - 8, -h / 2 - 1, 4)
    draw_circle(-w / 2 + 8, h / 2 + 1, 4)
    draw_circle(w / 2 - 8, h / 2 + 1, 4)

    glColor3f(1, 1, 0.7)
    draw_circle(w / 2, -5, 2.5)
    draw_circle(w / 2, 5, 2.5)

    glColor3f(0.85, 0.1, 0.1)
    draw_circle(-w / 2, -5, 2)
    draw_circle(-w / 2, 5, 2)

    glPopMatrix()


# =====================================================
# COLLISION AVOIDANCE
# =====================================================

def avoid_collision(c):
    for o in cars:
        if o == c:
            continue

        dx = o.x - c.x
        dy = o.y - c.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < MIN_GAP:
            front_x = math.cos(c.angle)
            front_y = math.sin(c.angle)

            dot = dx * front_x + dy * front_y

            if dot > 0:
                return True

    return False


# =====================================================
# SPAWN HELPERS
# =====================================================

def road_car_count(direction):
    count = 0

    for c in cars:
        if c.startDir == direction:
            count += 1

    return count


def start_position_for(direction):
    if direction == DIR_EAST:
        return -80, LANE_EAST

    if direction == DIR_NORTH:
        return LANE_NORTH, -80

    if direction == DIR_WEST:
        return WIN_W + 80, LANE_WEST

    return LANE_SOUTH, WIN_H + 80


def can_spawn_on_road(direction):
    # Do not add if total car limit reached
    if len(cars) >= MAX_CARS:
        return False

    # Do not add if this road already has too many cars
    if road_car_count(direction) >= MAX_CARS_PER_ROAD:
        return False

    sx, sy = start_position_for(direction)

    # Do not add if spawn point is blocked
    for c in cars:
        if distance(sx, sy, c.x, c.y) < MIN_GAP * 2:
            return False

    return True


def spawn_car(direction=None):
    global totalSpawned, spawnCursor

    # If fixed direction is requested, only add if that road has space
    if direction is not None:
        if can_spawn_on_road(direction):
            cars.append(Car(direction))
            totalSpawned += 1
        return

    # Balanced auto spawn:
    # Try roads one by one, so cars do not come from only one road.
    for i in range(4):
        d = (spawnCursor + i) % 4

        if can_spawn_on_road(d):
            cars.append(Car(d))
            totalSpawned += 1
            spawnCursor = (d + 1) % 4
            return

    # If all roads are full, no car is added.


# =====================================================
# UPDATE CARS
# =====================================================

def update_cars():
    global carsPassed

    remove_list = []

    for c in cars:
        desired = c.speed

        # Stop before yellow line if signal is not green
        if c.targetIndex == 1 and not signal_allows(c.startDir):
            tx, ty = c.path[1]
            d = distance(c.x, c.y, tx, ty)

            if d < 90:
                desired = max(0, d * 0.08)

            if d < 5:
                desired = 0

        # Maintain gap
        if avoid_collision(c):
            desired = 0

        c.curSpeed = desired

        if c.targetIndex < len(c.path):
            tx, ty = c.path[c.targetIndex]

            c.angle = angle_to_point(c.x, c.y, tx, ty)
            d = distance(c.x, c.y, tx, ty)

            # Do not cross hidden stop point unless green
            if c.targetIndex == 1 and not signal_allows(c.startDir) and d < 5:
                continue

            step = min(c.curSpeed, d)

            c.x += math.cos(c.angle) * step
            c.y += math.sin(c.angle) * step

            if distance(c.x, c.y, tx, ty) < 4:
                c.x = tx
                c.y = ty
                c.targetIndex += 1

        # Count car after passing intersection
        if not c.counted:
            if c.targetIndex > 1:
                c.counted = True
                carsPassed += 1

        # Remove car after it leaves screen
        if c.x < -160 or c.x > WIN_W + 160 or c.y < -160 or c.y > WIN_H + 160:
            remove_list.append(c)

    for c in remove_list:
        cars.remove(c)


# =====================================================
# HUD AND USER INTERACTION COMMANDS
# =====================================================

def draw_hud():
    glColor3f(1, 1, 1)

    draw_text(20, WIN_H - 40, "TRAFFIC SIMULATION")
    draw_text(20, WIN_H - 70, f"Cars : {len(cars)}")
    draw_text(20, WIN_H - 100, f"Passed : {carsPassed}")
    draw_text(20, WIN_H - 130, f"Spawned : {totalSpawned}")

    mode = "NIGHT" if nightMode else "DAY"
    status = "RUNNING" if running else "PAUSED"

    draw_text(20, WIN_H - 160, f"Mode : {mode}")
    draw_text(20, WIN_H - 190, f"Status : {status}")

    phase_names = [
        "East Green",
        "East Yellow",
        "North Yellow",
        "North Green",
        "North Yellow",
        "West Yellow",
        "West Green",
        "West Yellow",
        "South Yellow",
        "South Green",
        "South Yellow",
        "East Yellow"
    ]

    draw_text(20, WIN_H - 220, f"Signal : {phase_names[curPhase]}")
    draw_text(20, WIN_H - 250, f"Green Time : {greenTime // 1000}s")

    draw_text(20, 150, "USER CONTROLS")
    draw_text(20, 120, "S  : Start / Stop Simulation")
    draw_text(20, 95,  "A  : Add New Car")
    draw_text(20, 70,  "+  : Increase Signal Time")
    draw_text(20, 45,  "-  : Decrease Signal Time")
    draw_text(20, 20,  "N  : Day / Night Mode")


# =====================================================
# DISPLAY
# =====================================================

def display():
    glClear(GL_COLOR_BUFFER_BIT)

    draw_background()
    draw_footpaths()
    draw_buildings()
    draw_roads()
    draw_signals()

    for c in cars:
        draw_car(c)

    draw_hud()

    glutSwapBuffers()


# =====================================================
# TIMER
# =====================================================

def timer(value):
    global spawnTimer

    if running:
        dt = 16

        update_signals(dt)
        update_cars()

        spawnTimer += dt

        if spawnTimer >= SPAWN_INTERVAL:
            spawnTimer = 0
            spawn_car()

    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)


# =====================================================
# KEYBOARD CONTROLS
# =====================================================

def keyboard(key, x, y):
    global running, greenTime, nightMode
    global carsPassed, totalSpawned, curPhase, phaseTimer
    global spawnCursor

    key = key.decode("utf-8")

    if key in ['s', 'S']:
        running = not running

    elif key in ['a', 'A']:
        spawn_car()

    elif key == '1':
        spawn_car(DIR_EAST)

    elif key == '2':
        spawn_car(DIR_NORTH)

    elif key == '3':
        spawn_car(DIR_WEST)

    elif key == '4':
        spawn_car(DIR_SOUTH)

    elif key in ['+', '=']:
        greenTime = min(greenTime + 1000, 15000)

    elif key in ['-', '_']:
        greenTime = max(greenTime - 1000, 2000)

    elif key in ['n', 'N']:
        nightMode = not nightMode

    elif key in ['r', 'R']:
        cars.clear()

        carsPassed = 0
        totalSpawned = 0
        spawnCursor = 0

        curPhase = PHASE_E_GREEN
        phaseTimer = 0

    elif key == '\x1b' or key in ['q', 'Q']:
        exit()

    glutPostRedisplay()


# =====================================================
# RESHAPE
# =====================================================

def reshape(w, h):
    glViewport(0, 0, w, h)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    gluOrtho2D(0, WIN_W, 0, WIN_H)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


# =====================================================
# INIT
# =====================================================

def init():
    glClearColor(0.55, 0.78, 0.50, 1)
    gluOrtho2D(0, WIN_W, 0, WIN_H)

    # Spawn one car from each road initially
    for i in range(4):
        spawn_car(i)


# =====================================================
# MAIN
# =====================================================

def main():
    glutInit()

    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(WIN_W, WIN_H)

    glutCreateWindow(b"Traffic Simulation - Balanced Car Spawn")

    init()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(16, timer, 0)

    glutMainLoop()


if __name__ == "__main__":
    main()
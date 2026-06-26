from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import sys

# ─────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────
WINDOW_W, WINDOW_H = 800, 400
GROUND_Y = 0.12       # normalised ground line
GRAVITY   = -0.010
JUMP_VEL  = 0.12

state = {
    "started":   False,
    "game_over": False,
    "won":       False,
    "score":     0.0,
    "speed":     0.008,
    "frame":     0,
}

boy = {"x": 0.18, "y": GROUND_Y, "vy": 0.0, "jumping": False}
girl = {"x": 0.72, "y": GROUND_Y}

obstacles = []      # list of {"x", "type"}  type 0=bush, 1=wall
obs_timer  = 0
obs_interval = 90

hearts = []         # floating hearts {"x","y","vy","life"}
stars  = [(random.uniform(0.01, 0.99), random.uniform(0.55, 0.98)) for _ in range(40)]


# ─────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────
def draw_rect(x, y, w, h):
    glBegin(GL_QUADS)
    glVertex2f(x,     y)
    glVertex2f(x + w, y)
    glVertex2f(x + w, y + h)
    glVertex2f(x,     y + h)
    glEnd()

def draw_circle(cx, cy, r, segs=24):
    glBegin(GL_POLYGON)
    for i in range(segs):
        a = 2 * math.pi * i / segs
        glVertex2f(cx + r * math.cos(a), cy + r * math.sin(a))
    glEnd()

def draw_heart(cx, cy, size, alpha=1.0):
    glColor4f(1.0, 0.15, 0.5, alpha)
    glBegin(GL_POLYGON)
    for i in range(60):
        t = 2 * math.pi * i / 60
        hx = size * (16 * math.sin(t)**3)
        hy = size * (13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t))
        glVertex2f(cx + hx * 0.0008, cy + hy * 0.0008)
    glEnd()


# ─────────────────────────────────────────
#  CHARACTER DRAWING  (OpenGL polygons)
# ─────────────────────────────────────────
def draw_boy(x, y, phase, excited=False):
    S = 0.048          # scale unit

    # --- legs (two quads, animated) ---
    la = math.sin(phase * 2.5) * 0.018
    lb = math.cos(phase * 2.5) * 0.018
    glColor3f(0.15, 0.15, 0.15)
    draw_rect(x - 0.012, y - 0.004,  0.011, -(S * 0.55 + la))
    draw_rect(x + 0.001, y - 0.004,  0.011, -(S * 0.55 + lb))

    # --- shirt body (quad) ---
    glColor3f(0.75, 0.18, 0.12)
    draw_rect(x - S * 0.45, y, S * 0.9, S * 1.15)

    # --- jeans (quad below shirt) ---
    glColor3f(0.16, 0.28, 0.62)
    draw_rect(x - S * 0.45, y - S * 0.4, S * 0.9, S * 0.42)

    # --- head (circle) ---
    glColor3f(0.94, 0.72, 0.56)
    draw_circle(x, y + S * 1.4, S * 0.52)

    # --- hair (polygon arc) ---
    glColor3f(0.18, 0.10, 0.03)
    glBegin(GL_POLYGON)
    for i in range(12):
        a = math.pi * i / 11
        glVertex2f(x + S * 0.52 * math.cos(a), y + S * 1.4 + S * 0.52 * math.sin(a))
    glEnd()

    # --- arms (lines as thin quads) ---
    arm_swing = math.sin(phase * 2.5) * 0.022 + (0.01 * math.sin(state["frame"] * 0.3) if excited else 0)
    glColor3f(0.75, 0.18, 0.12)
    # left arm
    draw_rect(x - S * 0.45 - 0.014, y + S * 0.5 + arm_swing, 0.013, S * 0.7)
    # right arm
    draw_rect(x + S * 0.45 + 0.001, y + S * 0.5 - arm_swing, 0.013, S * 0.7)

    # --- love indicator: heart above head when close ---
    if state["score"] > 40:
        alpha = min(1.0, (state["score"] - 40) / 30)
        pulse = 0.5 + 0.5 * math.sin(state["frame"] * 0.12)
        draw_heart(x, y + S * 2.4, (6 + pulse * 3), alpha * pulse)


def draw_girl(x, y, phase):
    S = 0.046

    # --- legs ---
    la = math.sin(phase * 2.5) * 0.016
    lb = math.cos(phase * 2.5) * 0.016
    glColor3f(0.96, 0.78, 0.62)
    draw_rect(x - 0.010, y - 0.004, 0.009, -(S * 0.45 + la))
    draw_rect(x + 0.001, y - 0.004, 0.009, -(S * 0.45 + lb))

    # --- dress / skirt (trapezoid — GL_POLYGON) ---
    glColor3f(0.91, 0.12, 0.55)
    glBegin(GL_POLYGON)
    glVertex2f(x - S * 0.38, y)
    glVertex2f(x + S * 0.38, y)
    glVertex2f(x + S * 0.72, y - S * 0.7)
    glVertex2f(x - S * 0.72, y - S * 0.7)
    glEnd()

    # --- top (quad) ---
    glColor3f(1.0, 0.42, 0.76)
    draw_rect(x - S * 0.40, y, S * 0.80, S * 1.10)

    # --- head ---
    glColor3f(0.96, 0.78, 0.62)
    draw_circle(x, y + S * 1.48, S * 0.50)

    # --- hair (polygon) ---
    glColor3f(0.42, 0.20, 0.04)
    glBegin(GL_POLYGON)
    for i in range(12):
        a = math.pi * i / 11
        glVertex2f(x + S * 0.52 * math.cos(a), y + S * 1.48 + S * 0.52 * math.sin(a))
    glEnd()
    # side ponytail
    glBegin(GL_POLYGON)
    pts = [(S*0.50, S*1.62),(S*0.80, S*1.50),(S*0.82, S*1.15),(S*0.52, S*1.10)]
    for px, py in pts:
        glVertex2f(x + px, y + py)
    glEnd()

    # --- arms ---
    arm_swing = math.sin(phase * 2.5) * 0.020
    glColor3f(1.0, 0.42, 0.76)
    draw_rect(x - S * 0.40 - 0.013, y + S * 0.5 + arm_swing, 0.012, S * 0.65)
    draw_rect(x + S * 0.40 + 0.001, y + S * 0.5 - arm_swing, 0.012, S * 0.65)


def draw_bush(x, y):
    # Three overlapping circles + stem
    glColor3f(0.06, 0.50, 0.18)
    draw_circle(x,        y + 0.072, 0.038)
    glColor3f(0.08, 0.44, 0.14)
    draw_circle(x - 0.04, y + 0.058, 0.028)
    draw_circle(x + 0.04, y + 0.058, 0.028)
    glColor3f(0.30, 0.15, 0.04)
    draw_rect(x - 0.008, y, 0.016, 0.032)


def draw_wall(x, y):
    # Stone wall (quad + brick lines)
    glColor3f(0.52, 0.26, 0.10)
    draw_rect(x - 0.028, y, 0.056, 0.130)
    glColor3f(0.36, 0.16, 0.06)
    draw_rect(x - 0.028, y + 0.126, 0.056, 0.006)
    # brick slots (GL_LINES)
    glColor3f(0.28, 0.12, 0.04)
    glLineWidth(1.5)
    glBegin(GL_LINES)
    for row in range(4):
        ry = y + row * 0.032
        glVertex2f(x - 0.028, ry); glVertex2f(x + 0.028, ry)
        offset = 0.014 if row % 2 == 0 else 0.0
        glVertex2f(x - 0.028 + offset, ry); glVertex2f(x - 0.028 + offset, ry + 0.030)
    glEnd()


def draw_background():
    # Sky gradient (two quads)
    glBegin(GL_QUADS)
    glColor3f(0.02, 0.01, 0.10); glVertex2f(0, 1)
    glColor3f(0.02, 0.01, 0.10); glVertex2f(1, 1)
    glColor3f(0.11, 0.04, 0.30); glVertex2f(1, GROUND_Y)
    glColor3f(0.11, 0.04, 0.30); glVertex2f(0, GROUND_Y)
    glEnd()

    # Stars
    glPointSize(2.5)
    glColor3f(1, 1, 0.9)
    glBegin(GL_POINTS)
    for sx, sy in stars:
        glVertex2f(sx, sy)
    glEnd()

    # Moon
    glColor3f(1.0, 1.0, 0.80)
    draw_circle(0.88, 0.82, 0.055)
    glColor3f(0.02, 0.01, 0.10)
    draw_circle(0.895, 0.838, 0.048)

    # City silhouette (GL_POLYGON buildings)
    glColor3f(0.06, 0.02, 0.18)
    buildings = [
        (0.00, 0.12, 0.07, 0.30), (0.07, 0.12, 0.05, 0.24),
        (0.12, 0.12, 0.08, 0.38), (0.20, 0.12, 0.06, 0.20),
        (0.26, 0.12, 0.07, 0.32), (0.33, 0.12, 0.09, 0.44),
        (0.42, 0.12, 0.06, 0.28), (0.48, 0.12, 0.07, 0.35),
        (0.55, 0.12, 0.08, 0.26), (0.63, 0.12, 0.06, 0.40),
        (0.69, 0.12, 0.09, 0.22), (0.78, 0.12, 0.07, 0.36),
        (0.85, 0.12, 0.06, 0.28), (0.91, 0.12, 0.09, 0.34),
    ]
    for bx, by, bw, bh in buildings:
        draw_rect(bx, by, bw, bh)

    # Ground
    glColor3f(0.13, 0.06, 0.38)
    draw_rect(0, 0, 1, GROUND_Y)
    glColor3f(0.20, 0.10, 0.52)
    draw_rect(0, GROUND_Y - 0.006, 1, 0.008)


def draw_hud():
    score_int = int(state["score"])

    # Score text via bitmap characters
    glColor3f(1, 1, 1)
    glRasterPos2f(0.02, 0.92)
    text = f"Score: {score_int} / 100"
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Progress bar background
    glColor4f(1, 1, 1, 0.2)
    draw_rect(0.02, 0.86, 0.30, 0.016)

    # Progress bar fill (colour shifts green→yellow→pink)
    pct = min(state["score"], 100) / 100
    r = min(1.0, pct * 2)
    g = max(0.0, 1.0 - pct)
    glColor3f(r, g, 0.6)
    draw_rect(0.02, 0.86, 0.30 * pct, 0.016)

    # Hint text early on
    if state["score"] < 6 and state["started"]:
        glColor3f(1.0, 1.0, 0.5)
        glRasterPos2f(0.28, 0.93)
        for ch in "SPACE / UP to jump!":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(ch))


def draw_floating_hearts():
    for h in hearts:
        draw_heart(h["x"], h["y"], 5, h["life"])


def draw_text_centered(text, y, font=GLUT_BITMAP_HELVETICA_18):
    w = sum(glutBitmapWidth(font, ord(c)) for c in text)
    # convert pixel width to normalised coords
    nx = 0.5 - (w / (2 * WINDOW_W))
    glRasterPos2f(nx, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))


def draw_start_screen():
    glColor4f(0, 0, 0, 0.55)
    draw_rect(0, 0, 1, 1)

    glColor3f(1.0, 0.92, 0.15)
    draw_text_centered("LOVE  CHASE", 0.72, GLUT_BITMAP_TIMES_ROMAN_24)

    glColor3f(1.0, 0.65, 0.80)
    draw_text_centered("Help Saiful jump over obstacles and reach his girl!", 0.58, GLUT_BITMAP_HELVETICA_12)
    draw_text_centered("Score 100 to reunite!  <3", 0.52, GLUT_BITMAP_HELVETICA_12)

    # Blinking prompt
    if (state["frame"] // 25) % 2 == 0:
        glColor3f(1, 1, 1)
        draw_text_centered("Press SPACE or ENTER to start", 0.38, GLUT_BITMAP_HELVETICA_18)


def draw_win_screen():
    glColor4f(0, 0, 0, 0.50)
    draw_rect(0, 0, 1, 1)

    glColor3f(1.0, 0.92, 0.15)
    draw_text_centered("HELLO  FIRST  LOVE!", 0.78, GLUT_BITMAP_TIMES_ROMAN_24)
    glColor3f(1.0, 0.70, 0.85)
    draw_text_centered("Saiful finally reached his girl!  <3", 0.67, GLUT_BITMAP_HELVETICA_18)

    for i in range(12):
        a = state["frame"] * 0.025 + i * math.pi * 2 / 12
        r = 0.13 + 0.03 * math.sin(state["frame"] * 0.06 + i)
        draw_heart(0.5 + math.cos(a) * r, GROUND_Y + 0.18 + math.sin(a) * r * 0.5,
                   7, 0.7 + 0.3 * math.sin(a))

    glColor3f(0.8, 0.8, 0.8)
    draw_text_centered("Press SPACE or ENTER to play again", 0.15, GLUT_BITMAP_HELVETICA_12)


def draw_game_over_screen():
    glColor4f(0, 0, 0, 0.60)
    draw_rect(0, 0, 1, 1)

    glColor3f(1.0, 0.25, 0.25)
    draw_text_centered("GAME  OVER", 0.72, GLUT_BITMAP_TIMES_ROMAN_24)
    glColor3f(1.0, 0.75, 0.75)
    draw_text_centered(f"Score: {int(state['score'])}", 0.58, GLUT_BITMAP_HELVETICA_18)
    draw_text_centered("She got away... try again!", 0.48, GLUT_BITMAP_HELVETICA_12)
    glColor3f(0.8, 0.8, 0.8)
    draw_text_centered("Press SPACE or ENTER to retry", 0.22, GLUT_BITMAP_HELVETICA_12)


# ─────────────────────────────────────────
#  GAME LOGIC
# ─────────────────────────────────────────
def check_collision():
    bx, by = boy["x"], boy["y"]
    for o in obstacles:
        hw = 0.04
        oh = 0.14 if o["type"] == 1 else 0.10
        if abs(bx - o["x"]) < hw and by < GROUND_Y + oh:
            return True
    return False


def reset_game():
    state.update({"started": True, "game_over": False, "won": False,
                  "score": 0.0, "speed": 0.008, "frame": 0})
    boy.update({"x": 0.18, "y": GROUND_Y, "vy": 0.0, "jumping": False})
    girl.update({"x": 0.72, "y": GROUND_Y})
    obstacles.clear()
    hearts.clear()
    global obs_timer, obs_interval
    obs_timer = 0
    obs_interval = 90


# ─────────────────────────────────────────
#  GLUT CALLBACKS
# ─────────────────────────────────────────
def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    draw_background()

    phase = state["frame"] * 0.13

    if not state["started"]:
        draw_girl(girl["x"], girl["y"], phase)
        draw_boy(boy["x"], boy["y"], phase)
        draw_start_screen()
    elif state["won"]:
        draw_girl(0.48, GROUND_Y, 0)
        draw_boy(0.54, GROUND_Y, 0, excited=True)
        draw_floating_hearts()
        draw_win_screen()
    elif state["game_over"]:
        for o in obstacles:
            if   o["type"] == 0: draw_bush(o["x"], o["y"])
            elif o["type"] == 1: draw_wall(o["x"], o["y"])
        draw_girl(girl["x"], girl["y"], 0)
        draw_boy(boy["x"], boy["y"], 0)
        draw_floating_hearts()
        draw_hud()
        draw_game_over_screen()
    else:
        for o in obstacles:
            if   o["type"] == 0: draw_bush(o["x"], o["y"])
            elif o["type"] == 1: draw_wall(o["x"], o["y"])
        draw_girl(girl["x"], girl["y"], phase)
        draw_boy(boy["x"], boy["y"], phase,
                 excited=(state["score"] > 70))
        draw_floating_hearts()
        draw_hud()

    glutSwapBuffers()


def update(value):
    global obs_timer, obs_interval

    state["frame"] += 1

    if not state["started"] or state["game_over"] or state["won"]:
        glutTimerFunc(16, update, 0)
        glutPostRedisplay()
        return

    # Boy physics
    boy["vy"] += GRAVITY
    boy["y"]  += boy["vy"]
    
    # Ground collision - only land if falling and below ground
    if boy["y"] < GROUND_Y and boy["vy"] <= 0:
        boy["y"]  = GROUND_Y
        boy["vy"] = 0.0
        boy["jumping"] = False
    elif boy["y"] < GROUND_Y:
        # Prevent going below ground if somehow moving upward
        boy["y"] = GROUND_Y

    # Girl moves toward boy as score rises
    target_x = max(0.42, 0.72 - state["score"] * 0.003)
    girl["x"] += (target_x - girl["x"]) * 0.015

    # Obstacles
    obs_timer += 1
    if obs_timer >= obs_interval:
        obstacles.append({"x": 1.08, "y": GROUND_Y,
                          "type": random.choice([0, 0, 1])})
        obs_timer    = 0
        obs_interval = max(45, 90 - int(state["score"]) // 2)

    spd = state["speed"]
    for o in obstacles:
        o["x"] -= spd
    obstacles[:] = [o for o in obstacles if o["x"] > -0.1]

    # Score & speed
    state["score"] += 0.06 * (spd / 0.008)
    state["speed"]  = min(0.022, 0.008 + state["score"] * 0.00015)

    # Floating hearts
    if state["frame"] % 14 == 0 and state["score"] > 25:
        hearts.append({"x": boy["x"] + 0.01,
                       "y": boy["y"] + 0.14,
                       "vy": 0.004, "life": 1.0})
    for h in hearts:
        h["y"]    += h["vy"]
        h["life"] -= 0.018
    hearts[:] = [h for h in hearts if h["life"] > 0]

    # Win condition
    if state["score"] >= 100:
        state["won"]   = True
        state["score"] = 100
        glutTimerFunc(16, update, 0)
        glutPostRedisplay()
        return

    # Collision
    if check_collision():
        state["game_over"] = True

    glutTimerFunc(16, update, 0)
    glutPostRedisplay()


def keyboard(key, x, y):
    k = key if isinstance(key, int) else ord(key)
    # SPACE = 32, ENTER = 13
    if k in (32, 13, b' '[0]):
        if not state["started"] or state["game_over"] or state["won"]:
            reset_game()
        elif not boy["jumping"]:
            boy["vy"]      = JUMP_VEL
            boy["jumping"] = True


def special_keys(key, x, y):
    if key == GLUT_KEY_UP:
        if not state["started"] or state["game_over"] or state["won"]:
            reset_game()
        elif not boy["jumping"]:
            boy["vy"]      = JUMP_VEL
            boy["jumping"] = True


def init_gl():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_ALPHA)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Love Chase  -  Press SPACE to start")

    init_gl()

    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)
    glutTimerFunc(16, update, 0)

    glutMainLoop()


if __name__ == "__main__":
    main()
import sys
import os
import math
import random
import time
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# ============================================================
#  WINDOW & CONSTANTS
# ============================================================
WIN_W, WIN_H = 1100, 650
FPS          = 60
GROUND_Y     = 120

# ============================================================
#  GAME STATES
# ============================================================
STATE_STORY    = 0
STATE_MENU     = 1
STATE_GAME     = 2
STATE_PAUSED   = 3
STATE_GAMEOVER = 4
STATE_WIN      = 5

current_state      = STATE_STORY
prev_state         = STATE_STORY     # for pause resume

# ============================================================
#  GLOBAL TIMERS / MISC
# ============================================================
frame_count        = 0          # increments every timer tick
fade_alpha         = 1.0        # for fade-in/fade-out
fading_in          = True
fade_done          = False

# ============================================================
#  CG ALGORITHMS
# ============================================================

# -- 1. DDA Line --
def draw_line_dda(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    steps  = int(max(abs(dx), abs(dy)))
    if steps == 0:
        glBegin(GL_POINTS); glVertex2f(x1, y1); glEnd(); return
    xi, yi = dx / steps, dy / steps
    x, y   = float(x1), float(y1)
    glBegin(GL_POINTS)
    for _ in range(steps + 1):
        glVertex2f(round(x), round(y))
        x += xi; y += yi
    glEnd()

# -- 2. Bresenham Line --
def draw_line_bresenham(x1, y1, x2, y2):
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx     = 1 if x1 < x2 else -1
    sy     = 1 if y1 < y2 else -1
    err    = dx - dy
    glBegin(GL_POINTS)
    while True:
        glVertex2f(x1, y1)
        if x1 == x2 and y1 == y2: break
        e2 = 2 * err
        if e2 > -dy: err -= dy; x1 += sx
        if e2 <  dx: err += dx; y1 += sy
    glEnd()

# -- 3. Midpoint Circle --
def draw_circle_midpoint(xc, yc, r, filled=False):
    if r <= 0: return
    if filled:
        for ry in range(-int(r), int(r) + 1):
            rx = int(math.sqrt(max(0, r * r - ry * ry)))
            glBegin(GL_LINES)
            glVertex2f(xc - rx, yc + ry)
            glVertex2f(xc + rx, yc + ry)
            glEnd()
        return
    x, y = 0, int(r)
    p    = 1 - int(r)
    glBegin(GL_POINTS)
    def pts(x, y):
        for px, py in [(xc+x,yc+y),(xc-x,yc+y),(xc+x,yc-y),(xc-x,yc-y),
                       (xc+y,yc+x),(xc-y,yc+x),(xc+y,yc-x),(xc-y,yc-x)]:
            glVertex2f(px, py)
    pts(x, y)
    while x < y:
        x += 1
        if p < 0: p += 2*x + 1
        else:     y -= 1; p += 2*(x - y) + 1
        pts(x, y)
    glEnd()

# -- 4. Midpoint Ellipse --
def draw_ellipse_midpoint(xc, yc, rx, ry, filled=False):
    if filled:
        for dy in range(-int(ry), int(ry)+1):
            dx = int(rx * math.sqrt(max(0, 1 - (dy/ry)**2)))
            glBegin(GL_LINES)
            glVertex2f(xc - dx, yc + dy)
            glVertex2f(xc + dx, yc + dy)
            glEnd()
        return
    x, y   = 0, ry
    rx2, ry2 = rx*rx, ry*ry
    p      = ry2 - rx2*ry + 0.25*rx2
    glBegin(GL_POINTS)
    while 2*ry2*x < 2*rx2*y:
        for px,py in [(xc+x,yc+y),(xc-x,yc+y),(xc+x,yc-y),(xc-x,yc-y)]:
            glVertex2f(px, py)
        x += 1
        if p < 0: p += 2*ry2*x + ry2
        else:     y -= 1; p += 2*ry2*x - 2*rx2*y + ry2
    p = ry2*(x+0.5)**2 + rx2*(y-1)**2 - rx2*ry2
    while y >= 0:
        for px,py in [(xc+x,yc+y),(xc-x,yc+y),(xc+x,yc-y),(xc-x,yc-y)]:
            glVertex2f(px, py)
        y -= 1
        if p > 0: p -= 2*rx2*y + rx2
        else:     x += 1; p += 2*ry2*x - 2*rx2*y + rx2
    glEnd()

# -- 5. Cohen-Sutherland Line Clipping --
INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0,1,2,4,8
_CLIP = [0, WIN_W, GROUND_Y, WIN_H]
def _code(x, y):
    c = INSIDE
    if   x < _CLIP[0]: c |= LEFT
    elif x > _CLIP[1]: c |= RIGHT
    if   y < _CLIP[2]: c |= BOTTOM
    elif y > _CLIP[3]: c |= TOP
    return c
def cohen_sutherland(x1,y1,x2,y2):
    c1,c2 = _code(x1,y1), _code(x2,y2)
    while True:
        if not (c1|c2): return x1,y1,x2,y2,True
        if c1&c2:       return x1,y1,x2,y2,False
        c = c1 if c1 else c2
        if   c&TOP:    x = x1+(x2-x1)*(WIN_H-y1)/(y2-y1);  y=WIN_H
        elif c&BOTTOM: x = x1+(x2-x1)*(_CLIP[2]-y1)/(y2-y1); y=_CLIP[2]
        elif c&RIGHT:  y = y1+(y2-y1)*(_CLIP[1]-x1)/(x2-x1); x=_CLIP[1]
        else:          y = y1+(y2-y1)*(_CLIP[0]-x1)/(x2-x1); x=_CLIP[0]
        if c==c1: x1,y1,c1=x,y,_code(x,y)
        else:     x2,y2,c2=x,y,_code(x,y)

# ============================================================
#  HELPER DRAWING
# ============================================================
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glRasterPos2f(x, y)
    for ch in text:
        if 32 <= ord(ch) < 128:
            glutBitmapCharacter(font, ord(ch))

def draw_text_large(x, y, text):
    draw_text(x, y, text, GLUT_BITMAP_TIMES_ROMAN_24)

def draw_rect_filled(x, y, w, h):
    glBegin(GL_QUADS)
    glVertex2f(x,   y)
    glVertex2f(x+w, y)
    glVertex2f(x+w, y+h)
    glVertex2f(x,   y+h)
    glEnd()

def draw_rect_outline(x, y, w, h):
    glBegin(GL_LINE_LOOP)
    glVertex2f(x,   y)
    glVertex2f(x+w, y)
    glVertex2f(x+w, y+h)
    glVertex2f(x,   y+h)
    glEnd()

def draw_rounded_rect(x, y, w, h, r=8, segs=12):
    glBegin(GL_POLYGON)
    for corner_x, corner_y, start_ang in [
        (x+r,   y+r,   180), (x+w-r, y+r,   270),
        (x+w-r, y+h-r, 0),   (x+r,   y+h-r, 90)]:
        for i in range(segs+1):
            a = math.radians(start_ang + i*(90/segs))
            glVertex2f(corner_x + r*math.cos(a), corner_y + r*math.sin(a))
    glEnd()

def draw_overlay(alpha):
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(0,0,0,alpha)
    draw_rect_filled(0, 0, WIN_W, WIN_H)

# ============================================================
#  PARTICLES
# ============================================================
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=3, gravity=True):
        self.x, self.y   = x, y
        self.vx, self.vy = vx, vy
        self.color       = color
        self.life        = life
        self.max_life    = life
        self.size        = size
        self.gravity     = gravity

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        if self.gravity: self.vy -= 0.18
        self.life -= 1
        return self.life > 0

    def draw(self):
        alpha = self.life / self.max_life
        glEnable(GL_BLEND)
        glPointSize(self.size * alpha + 1)
        glColor4f(*self.color[:3], alpha * (self.color[3] if len(self.color)==4 else 1.0))
        glBegin(GL_POINTS)
        glVertex2f(self.x, self.y)
        glEnd()

particles = []

def emit_dust(x, y):
    for _ in range(3):
        particles.append(Particle(x+random.uniform(-5,5), y+2,
            random.uniform(-1.5,1.5), random.uniform(0.5,2.0),
            (0.7,0.6,0.4,1), random.randint(15,30), size=4))

def emit_explosion(x, y):
    for _ in range(40):
        ang = random.uniform(0, math.pi*2)
        spd = random.uniform(2, 8)
        col = random.choice([(1,0.4,0,1),(1,0.8,0,1),(1,0.2,0.2,1),(1,1,1,1)])
        particles.append(Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
            col, random.randint(30,60), size=random.randint(3,7)))

def emit_firework(x, y):
    col = (random.random(), random.random(), random.random(), 1)
    for _ in range(60):
        ang = random.uniform(0, math.pi*2)
        spd = random.uniform(1, 7)
        particles.append(Particle(x, y, math.cos(ang)*spd, math.sin(ang)*spd,
            col, random.randint(40,80), size=random.randint(2,5), gravity=True))

def emit_confetti(x, y):
    for _ in range(5):
        col = (random.random(), random.random(), random.random(), 1)
        particles.append(Particle(x, y,
            random.uniform(-3,3), random.uniform(1,5),
            col, random.randint(60,120), size=random.randint(3,6), gravity=True))

def emit_hearts(x, y):
    for _ in range(3):
        particles.append(Particle(x+random.uniform(-20,20), y,
            random.uniform(-1,1), random.uniform(1,3),
            (1,0.2,0.4,1), random.randint(60,100), size=6, gravity=False))

def emit_smoke(x, y):
    for _ in range(2):
        particles.append(Particle(x+random.uniform(-5,5), y,
            random.uniform(-0.5,0.5), random.uniform(0.5,1.5),
            (0.5,0.5,0.5,0.6), random.randint(20,40), size=8, gravity=False))

# ============================================================
#  BACKGROUND ELEMENTS
# ============================================================
# Stars
stars = [(random.uniform(0, WIN_W), random.uniform(GROUND_Y+20, WIN_H),
          random.uniform(0.5,2.5)) for _ in range(120)]
# Clouds
clouds = [{'x': random.uniform(0, WIN_W), 'y': random.uniform(WIN_H*0.6, WIN_H*0.9),
           'speed': random.uniform(0.3,0.8), 'w': random.uniform(70,150),
           'h': random.uniform(25,45)} for _ in range(8)]
# Birds
birds = [{'x': random.uniform(0, WIN_W), 'y': random.uniform(WIN_H*0.7, WIN_H*0.95),
          'speed': random.uniform(0.8,2.0), 'phase': random.uniform(0, math.pi*2)} for _ in range(6)]

bg_scroll   = 0.0   # parallax scroll
fg_scroll   = 0.0   # foreground road scroll
day_time    = 0.0   # 0 = night, 1 = day

def update_background(speed_mult):
    global bg_scroll, fg_scroll, day_time
    bg_scroll  = (bg_scroll + 0.5 * speed_mult) % WIN_W
    fg_scroll  = (fg_scroll + 4.0 * speed_mult) % 120
    day_time   = (math.sin(frame_count * 0.002) + 1) * 0.5
    for c in clouds:
        c['x'] -= c['speed'] * speed_mult
        if c['x'] + c['w'] < 0: c['x'] = WIN_W + c['w']
    for b in birds:
        b['x'] -= b['speed'] * speed_mult
        if b['x'] < -20: b['x'] = WIN_W + 20

def draw_sky():
    # Day/night gradient sky
    night_bot = (0.02, 0.02, 0.12)
    night_top = (0.05, 0.05, 0.25)
    day_bot   = (0.3,  0.55, 0.9)
    day_top   = (0.1,  0.3,  0.7)
    t = day_time
    rb = night_bot[0]*(1-t)+day_bot[0]*t
    gb = night_bot[1]*(1-t)+day_bot[1]*t
    bb = night_bot[2]*(1-t)+day_bot[2]*t
    rt = night_top[0]*(1-t)+day_top[0]*t
    gt = night_top[1]*(1-t)+day_top[1]*t
    bt = night_top[2]*(1-t)+day_top[2]*t
    glBegin(GL_QUADS)
    glColor3f(rb, gb, bb); glVertex2f(0, GROUND_Y)
    glColor3f(rb, gb, bb); glVertex2f(WIN_W, GROUND_Y)
    glColor3f(rt, gt, bt); glVertex2f(WIN_W, WIN_H)
    glColor3f(rt, gt, bt); glVertex2f(0, WIN_H)
    glEnd()

def draw_stars():
    if day_time > 0.6: return
    alpha = 1.0 - day_time / 0.6
    glEnable(GL_BLEND)
    for sx, sy, sz in stars:
        px = (sx - bg_scroll * 0.2) % WIN_W
        pulse = 0.7 + 0.3 * math.sin(frame_count * 0.05 + sz)
        glPointSize(sz * pulse)
        glColor4f(1, 1, 0.9, alpha * pulse)
        glBegin(GL_POINTS); glVertex2f(px, sy); glEnd()

def draw_clouds():
    for c in clouds:
        alpha = 0.6 + 0.4 * day_time
        glColor4f(1, 1, 1, alpha * 0.8)
        draw_ellipse_midpoint(c['x'], c['y'], c['w']/2, c['h']/2, filled=True)
        glColor4f(0.95, 0.95, 0.95, alpha * 0.6)
        draw_ellipse_midpoint(c['x']-c['w']*0.2, c['y']-4, c['w']*0.35, c['h']*0.35, filled=True)
        draw_ellipse_midpoint(c['x']+c['w']*0.2, c['y']-4, c['w']*0.35, c['h']*0.35, filled=True)

def draw_birds():
    for b in birds:
        wing = math.sin(frame_count * 0.15 + b['phase']) * 6
        glColor4f(0.15, 0.1, 0.05, 0.85)
        glLineWidth(1.5)
        glBegin(GL_LINE_STRIP)
        glVertex2f(b['x']-10, b['y']+wing)
        glVertex2f(b['x'],    b['y'])
        glVertex2f(b['x']+10, b['y']+wing)
        glEnd()
        glLineWidth(1.0)

def draw_mountains():
    colors = [(0.15,0.2,0.15),(0.2,0.25,0.2),(0.25,0.3,0.25)]
    widths = [300, 220, 180]
    heights= [180, 140, 110]
    for i,(col,mw,mh) in enumerate(zip(colors,widths,heights)):
        off = (bg_scroll * (0.15 + i*0.05)) % (WIN_W + mw)
        glColor3f(*col)
        for start in range(-mw, WIN_W+mw, mw):
            cx = start - off
            glBegin(GL_TRIANGLES)
            glVertex2f(cx, GROUND_Y)
            glVertex2f(cx + mw/2, GROUND_Y + mh)
            glVertex2f(cx + mw, GROUND_Y)
            glEnd()

def draw_ground():
    # Road base
    glColor3f(0.25, 0.25, 0.28)
    draw_rect_filled(0, 0, WIN_W, GROUND_Y)
    # Grass strip
    glColor3f(0.15, 0.5, 0.15)
    draw_rect_filled(0, GROUND_Y-4, WIN_W, 8)
    # Road lines
    glColor3f(0.9, 0.8, 0.1)
    dash_w = 60
    for i in range(WIN_W // dash_w + 2):
        x = (i * dash_w - fg_scroll) % WIN_W
        glBegin(GL_QUADS)
        glVertex2f(x,    GROUND_Y - 18)
        glVertex2f(x+36, GROUND_Y - 18)
        glVertex2f(x+36, GROUND_Y - 12)
        glVertex2f(x,    GROUND_Y - 12)
        glEnd()
    # Sidewalk
    glColor3f(0.6, 0.58, 0.55)
    draw_rect_filled(0, GROUND_Y - 4, WIN_W, 4)

# ============================================================
#  PLAYER
# ============================================================
class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x        = 150.0
        self.y        = float(GROUND_Y)
        self.vy       = 0.0
        # Jump physics tuned for realism:
        # strong initial impulse, faster fall than rise (variable gravity)
        self.gravity_rise = -0.65   # gravity while going UP
        self.gravity_fall = -1.1    # stronger gravity while falling (snappier)
        self.jump_force   = 17.0    # initial upward velocity
        self.jumping  = False
        self.sliding  = False
        self.health   = 3
        self.inv_timer= 0       # invincibility frames after hit
        self.run_frame= 0
        self.width    = 32
        self.height   = 64
        self.alive    = True
        self.shake    = 0       # screen shake counter

    @property
    def hit_h(self):
        return 32 if self.sliding else self.height

    def jump(self):
        if not self.jumping:
            self.vy      = self.jump_force
            self.jumping = True

    def update(self):
        if not self.alive: return
        # Variable gravity: fall faster than rise for snappy feel
        grav = self.gravity_rise if self.vy > 0 else self.gravity_fall
        self.vy += grav
        # Cap fall speed so it feels controlled
        self.vy  = max(self.vy, -22)
        self.y  += self.vy
        if self.y <= GROUND_Y:
            self.y       = GROUND_Y
            self.vy      = 0
            self.jumping = False
        if self.inv_timer > 0:
            self.inv_timer -= 1
        self.run_frame = (self.run_frame + 1) % 30
        if self.y == GROUND_Y and not self.sliding:
            if frame_count % 8 == 0:
                emit_dust(self.x + self.width//2, self.y)

    def hit(self):
        if self.inv_timer > 0: return
        self.health   -= 1
        self.inv_timer = 90
        self.shake     = 20
        emit_explosion(self.x + self.width//2, self.y + self.height//2)
        if self.health <= 0:
            self.alive    = False
            self.inv_timer = 0   # stop blinking immediately on death

    def draw(self):
        x, y = self.x, self.y
        if self.inv_timer > 0 and (self.inv_timer // 5) % 2 == 0:
            return   # blink effect

        glPushMatrix()
        # Sliding posture
        if self.sliding:
            glTranslatef(x + self.width//2, y + 18, 0)
            glScalef(1.0, 0.5, 1.0)
            glTranslatef(-(x + self.width//2), -(y + 18), 0)

        leg_swing = math.sin(self.run_frame * math.pi / 15) * 8

        # --- Shoes ---
        glColor3f(0.1, 0.1, 0.1)
        draw_ellipse_midpoint(x+10, y+4,  10, 5, filled=True)
        draw_ellipse_midpoint(x+22, y+4,  10, 5, filled=True)

        # --- Legs ---
        glColor3f(0.2, 0.3, 0.7)
        draw_line_dda(x+8,  y+5,  x+8  + leg_swing,  y+28)
        draw_line_dda(x+24, y+5,  x+24 - leg_swing,  y+28)
        glLineWidth(4)
        glBegin(GL_LINES)
        glColor3f(0.2,0.3,0.7)
        glVertex2f(x+8,  y+6); glVertex2f(x+8  + leg_swing, y+30)
        glVertex2f(x+24, y+6); glVertex2f(x+24 - leg_swing, y+30)
        glEnd()
        glLineWidth(1)

        # --- Body ---
        glColor3f(0.15, 0.5, 0.95)
        draw_rounded_rect(x+4, y+28, self.width-8, 26, r=5)
        # Shirt stripe
        glColor3f(1.0, 0.9, 0.2)
        draw_rect_filled(x+4, y+38, self.width-8, 5)

        # --- Arms ---
        arm_swing = math.sin(self.run_frame * math.pi / 15) * 10
        glColor3f(0.9, 0.65, 0.45)
        glLineWidth(4)
        glBegin(GL_LINES)
        glVertex2f(x+4,    y+50); glVertex2f(x+4  - 10, y+40 + arm_swing)
        glVertex2f(x+28,   y+50); glVertex2f(x+28 + 10, y+40 - arm_swing)
        glEnd()
        glLineWidth(1)

        # --- Head (skin) ---
        glColor3f(0.95, 0.70, 0.48)
        draw_circle_midpoint(x + self.width//2, y+72, 14, filled=True)
        # Hair
        glColor3f(0.2, 0.1, 0.05)
        draw_ellipse_midpoint(x + self.width//2, y+80, 14, 8, filled=True)
        # Eyes
        glColor3f(0.1, 0.1, 0.1)
        draw_circle_midpoint(x + self.width//2 - 5, y+72, 2, filled=True)
        draw_circle_midpoint(x + self.width//2 + 5, y+72, 2, filled=True)
        # Mouth — small natural smile (arc, not filled ellipse)
        glColor3f(0.35, 0.15, 0.1)
        glLineWidth(1.5)
        glBegin(GL_LINE_STRIP)
        cx_m = x + self.width//2
        for step in range(7):
            angle = math.radians(200 + step * 20)   # 200°→320° = bottom arc
            glVertex2f(cx_m + math.cos(angle) * 4,
                       y + 66 + math.sin(angle) * 2.5)
        glEnd()
        glLineWidth(1)

        glPopMatrix()

    def get_aabb(self):
        return (self.x, self.y, self.x + self.width, self.y + self.hit_h)

# ============================================================
#  OBSTACLE TYPES
# ============================================================
class Car:
    def __init__(self, x):
        self.x, self.y = x, GROUND_Y
        self.w, self.h = 110, 55
        self.speed     = 6.0
        self.type      = "car"

    def update(self, mult):
        self.x -= self.speed * mult

    def draw(self):
        x, y, w, h = self.x, self.y, self.w, self.h
        # body
        glColor3f(0.8, 0.1, 0.1)
        draw_rounded_rect(x, y, w, h-8, r=8)
        # roof
        glColor3f(0.65, 0.08, 0.08)
        draw_rounded_rect(x+15, y+h-8, w-30, 22, r=6)
        # windows
        glColor4f(0.5, 0.8, 1.0, 0.7)
        draw_rect_filled(x+20, y+h-5, 28, 16)
        draw_rect_filled(x+54, y+h-5, 28, 16)
        # wheels
        glColor3f(0.15, 0.15, 0.15)
        draw_circle_midpoint(x+22, y+4, 12, filled=True)
        draw_circle_midpoint(x+w-22, y+4, 12, filled=True)
        glColor3f(0.6, 0.6, 0.6)
        draw_circle_midpoint(x+22, y+4, 6, filled=True)
        draw_circle_midpoint(x+w-22, y+4, 6, filled=True)
        # headlights
        glColor3f(1.0, 1.0, 0.6)
        draw_circle_midpoint(x+w-5, y+25, 5, filled=True)
        # exhaust
        if frame_count % 3 == 0:
            emit_smoke(x, y+20)

    def get_aabb(self):
        return (self.x+10, self.y, self.x+self.w-10, self.y+self.h+20)

class Barrier:
    def __init__(self, x):
        self.x, self.y = x, GROUND_Y
        self.w, self.h = 24, 70
        self.speed     = 5.5
        self.type      = "barrier"

    def update(self, mult):
        self.x -= self.speed * mult

    def draw(self):
        x, y, w, h = self.x, self.y, self.w, self.h
        # pole
        glColor3f(0.9, 0.9, 0.9)
        draw_rect_filled(x+8, y, 8, h)
        # stripes
        stripe_h = 14
        for i in range(4):
            col = (0.95,0.2,0.1) if i%2==0 else (0.95,0.9,0.9)
            glColor3f(*col)
            draw_rect_filled(x+8, y + i*stripe_h, 8, stripe_h)
        # top cone
        glColor3f(0.9, 0.9, 0.9)
        glBegin(GL_TRIANGLES)
        glVertex2f(x+4,  y+h)
        glVertex2f(x+20, y+h)
        glVertex2f(x+12, y+h+16)
        glEnd()

    def get_aabb(self):
        return (self.x+6, self.y, self.x+self.w-6, self.y+self.h)

class Rock:
    def __init__(self, x):
        self.x, self.y = x, GROUND_Y
        self.r         = random.randint(20, 35)
        self.speed     = 5.0
        self.type      = "rock"

    def update(self, mult):
        self.x -= self.speed * mult

    def draw(self):
        glColor3f(0.5, 0.48, 0.45)
        draw_circle_midpoint(self.x, self.y + self.r, self.r, filled=True)
        glColor3f(0.65, 0.62, 0.6)
        draw_circle_midpoint(self.x-4, self.y + self.r+5, self.r-6, filled=True)

    def get_aabb(self):
        return (self.x - self.r + 6, self.y,
                self.x + self.r - 6, self.y + self.r*2 - 4)

class Box:
    def __init__(self, x):
        s          = random.randint(36, 52)
        self.x, self.y = x, GROUND_Y
        self.w = self.h = s
        self.speed = 5.0
        self.type  = "box"

    def update(self, mult):
        self.x -= self.speed * mult

    def draw(self):
        x, y, w, h = self.x, self.y, self.w, self.h
        glColor3f(0.75, 0.55, 0.2)
        draw_rect_filled(x, y, w, h)
        glColor3f(0.6, 0.4, 0.1)
        draw_line_dda(x, y+h//2, x+w, y+h//2)
        draw_line_dda(x+w//2, y, x+w//2, y+h)
        glColor3f(0.9, 0.8, 0.5)
        draw_rect_outline(x, y, w, h)

    def get_aabb(self):
        return (self.x, self.y, self.x+self.w, self.y+self.h)

class Dog:
    def __init__(self, x):
        self.x, self.y = x, GROUND_Y
        self.w, self.h = 55, 35
        self.speed     = 7.0
        self.frame     = 0
        self.type      = "dog"

    def update(self, mult):
        self.x -= self.speed * mult
        self.frame = (self.frame + 1) % 20

    def draw(self):
        x, y = self.x, self.y
        leg  = math.sin(self.frame * math.pi / 10) * 5
        # Body
        glColor3f(0.55, 0.38, 0.2)
        draw_ellipse_midpoint(x+22, y+18, 22, 12, filled=True)
        # Head
        glColor3f(0.6, 0.42, 0.22)
        draw_circle_midpoint(x+44, y+25, 11, filled=True)
        # Ears
        glBegin(GL_TRIANGLES)
        glVertex2f(x+38, y+34); glVertex2f(x+44, y+40); glVertex2f(x+48, y+34)
        glEnd()
        # Eyes
        glColor3f(0.1,0.1,0.1)
        draw_circle_midpoint(x+48, y+27, 2, filled=True)
        # Nose
        glColor3f(0.2,0.1,0.1)
        draw_circle_midpoint(x+55, y+24, 3, filled=True)
        # Legs
        glColor3f(0.5, 0.35, 0.15)
        glLineWidth(3)
        glBegin(GL_LINES)
        glVertex2f(x+10, y+8); glVertex2f(x+10-leg,  y)
        glVertex2f(x+18, y+8); glVertex2f(x+18+leg,  y)
        glVertex2f(x+30, y+8); glVertex2f(x+30-leg,  y)
        glVertex2f(x+38, y+8); glVertex2f(x+38+leg,  y)
        glEnd()
        glLineWidth(1)
        # Tail
        glColor3f(0.55, 0.38, 0.2)
        glBegin(GL_LINE_STRIP)
        glVertex2f(x, y+22)
        glVertex2f(x-8, y+28+leg)
        glVertex2f(x-14, y+35+leg)
        glEnd()

    def get_aabb(self):
        return (self.x+5, self.y, self.x+self.w, self.y+self.h)

OBSTACLE_CLASSES = [Car, Barrier, Rock, Box, Dog]

# ============================================================
#  KIDNAPPER CAR (story + win scene)
# ============================================================
class KidnapperCar:
    def __init__(self, start_x, direction=1):
        self.x   = start_x
        self.y   = GROUND_Y
        self.spd = 0
        self.dir = direction  # 1=right, -1=left

    def draw(self):
        x, y = self.x, self.y
        # Body
        glColor3f(0.05, 0.05, 0.05)
        draw_rounded_rect(x, y, 120, 48, r=8)
        # Roof
        glColor3f(0.1, 0.1, 0.1)
        draw_rounded_rect(x+15, y+40, 90, 24, r=6)
        # Tinted windows
        glColor4f(0.2, 0.5, 0.8, 0.4)
        draw_rect_filled(x+20, y+42, 35, 18)
        draw_rect_filled(x+62, y+42, 35, 18)
        # Wheels
        glColor3f(0.1,0.1,0.1)
        draw_circle_midpoint(x+25, y+6, 13, filled=True)
        draw_circle_midpoint(x+95, y+6, 13, filled=True)
        glColor3f(0.5,0.5,0.5)
        draw_circle_midpoint(x+25, y+6, 6, filled=True)
        draw_circle_midpoint(x+95, y+6, 6, filled=True)
        # Red light
        glColor3f(1,0.1,0.1)
        draw_circle_midpoint(x+2 if self.dir<0 else x+118, y+30, 5, filled=True)

# ============================================================
#  GIRL CHARACTER
# ============================================================
class Girl:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.run_frame = 0

    def draw(self, run=False):
        x, y = self.x, self.y
        leg  = math.sin(self.run_frame * math.pi / 15) * 7 if run else 0

        # Shoes
        glColor3f(0.15, 0.05, 0.05)
        draw_ellipse_midpoint(x+8,  y+4, 9, 4, filled=True)
        draw_ellipse_midpoint(x+22, y+4, 9, 4, filled=True)

        # Legs / dress
        glColor3f(0.9, 0.3, 0.5)
        glBegin(GL_TRIANGLES)
        glVertex2f(x+4, y+30)
        glVertex2f(x+26, y+30)
        glVertex2f(x+15, y)
        glEnd()

        # Dress body
        glColor3f(0.95, 0.35, 0.55)
        draw_rounded_rect(x+5, y+28, 20, 24, r=5)
        # Bow
        glColor3f(1.0, 0.8, 0.9)
        draw_ellipse_midpoint(x+9,  y+46, 5, 3, filled=True)
        draw_ellipse_midpoint(x+21, y+46, 5, 3, filled=True)

        # Arms
        glColor3f(0.95, 0.72, 0.52)
        glLineWidth(3)
        glBegin(GL_LINES)
        glVertex2f(x+5,  y+46); glVertex2f(x-4,  y+36)
        glVertex2f(x+25, y+46); glVertex2f(x+34, y+36)
        glEnd()
        glLineWidth(1)

        # Head
        glColor3f(0.95, 0.72, 0.52)
        draw_circle_midpoint(x+15, y+66, 12, filled=True)
        # Hair
        glColor3f(0.35, 0.18, 0.05)
        draw_ellipse_midpoint(x+15, y+73, 13, 8, filled=True)
        # Ponytail
        glBegin(GL_LINE_STRIP)
        glVertex2f(x+26, y+68); glVertex2f(x+34, y+60); glVertex2f(x+32, y+50)
        glEnd()
        # Eyes
        glColor3f(0.1, 0.05, 0.2)
        draw_circle_midpoint(x+10, y+65, 2, filled=True)
        draw_circle_midpoint(x+20, y+65, 2, filled=True)
        # Smile
        glColor3f(0.7, 0.2, 0.3)
        draw_ellipse_midpoint(x+15, y+59, 4, 2)

        if run: self.run_frame = (self.run_frame+1) % 30

# ============================================================
#  STORY MODE
# ============================================================
story_lines = [
    "A boy deeply loves a girl.",
    "Every time they try to be together, life creates obstacles.",
    "Despite everything, the boy never gives up.",
    "He gathers enough courage to confess his feelings...",
    "He tells her everything that was always in his heart.",
    "The girl smiles...",
    "and happily says...  YES! <3",
]
story_idx      = 0
story_char     = 0.0
story_hold     = 0       # hold counter after full line
STORY_SPEED    = 0.35    # chars per frame
HOLD_FRAMES    = 80

# Kidnap scene variables
kidnap_phase   = 0      # 0=not started,1=car in,2=pause,3=car out,4=done
kidnap_car     = None
kidnap_girl    = None
kidnap_timer   = 0
story_done     = False  # True once we should go to menu

def advance_story():
    global story_idx, story_char, story_hold, kidnap_phase, kidnap_car, kidnap_girl, story_done
    story_idx  += 1
    story_char  = 0.0
    story_hold  = 0
    if story_idx >= len(story_lines):
        # Start kidnap cinematic
        if kidnap_phase == 0:
            kidnap_phase = 1
            kidnap_car   = KidnapperCar(-140, direction=1)
            kidnap_car.spd = 0
            kidnap_girl  = Girl(WIN_W//2 - 40, GROUND_Y)

# ============================================================
#  MENU
# ============================================================
menu_selected = 0
game_started  = False   # True once a game session has begun (enables Resume)

# ============================================================
#  GAME STATE
# ============================================================
player     = Player()
obstacles  = []
spawn_timer= 0
spawn_delay= 90
score      = 0.0
speed_mult = 1.0
health     = 3

# Win scene
win_girl_x  = WIN_W + 60
win_timer   = 0
win_phase   = 0   # 0=running girl, 1=hug, 2=fireworks

firework_timer = 0

def reset_game():
    global obstacles, spawn_timer, score, speed_mult, health, win_girl_x, win_timer, win_phase
    global firework_timer
    player.reset()
    obstacles   = []
    spawn_timer = 0
    spawn_delay = 90
    score       = 0.0
    speed_mult  = 1.0
    health      = 3
    win_girl_x  = WIN_W + 60
    win_timer   = 0
    win_phase   = 0
    firework_timer = 0

# ============================================================
#  AABB COLLISION
# ============================================================
def aabb_check(ax1,ay1,ax2,ay2, bx1,by1,bx2,by2):
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

# ============================================================
#  DRAW HUD (health hearts + score bar)
# ============================================================
def draw_hud():
    # Score bar background
    glColor4f(0,0,0,0.4)
    draw_rounded_rect(10, WIN_H-50, 300, 40, r=8)
    glColor3f(1,1,1)
    draw_text(20, WIN_H-34, f"Score: {int(score)} / 100", GLUT_BITMAP_HELVETICA_18)
    # Score fill
    pct = min(score / 100.0, 1.0)
    glColor3f(0.2, 0.9, 0.4)
    draw_rounded_rect(12, WIN_H-48, int(296*pct), 36, r=6)
    glColor3f(1,1,1)
    draw_text(20, WIN_H-34, f"Score: {int(score)} / 100", GLUT_BITMAP_HELVETICA_18)

    # Health hearts
    for i in range(3):
        if i < health:
            glColor3f(1.0, 0.15, 0.3)
        else:
            glColor3f(0.3, 0.15, 0.2)
        hx = WIN_W - 140 + i*44
        hy = WIN_H - 40
        # Heart shape via two circles + triangle
        draw_circle_midpoint(hx+8,  hy+12, 8, filled=True)
        draw_circle_midpoint(hx+20, hy+12, 8, filled=True)
        glBegin(GL_TRIANGLES)
        glVertex2f(hx,    hy+12)
        glVertex2f(hx+28, hy+12)
        glVertex2f(hx+14, hy)
        glEnd()

    # Speed badge
    glColor4f(0,0,0,0.4)
    draw_rounded_rect(WIN_W-130, 10, 120, 30, r=6)
    glColor3f(1,0.8,0.2)
    draw_text(WIN_W-122, 20, f"Speed {speed_mult:.1f}x", GLUT_BITMAP_HELVETICA_12)

def draw_hud():
    # --- Score bar ---
    bar_x, bar_y, bar_w, bar_h = 14, WIN_H-52, 280, 36
    glColor4f(0,0,0,0.5)
    draw_rounded_rect(bar_x-2, bar_y-2, bar_w+4, bar_h+4, r=8)
    glColor3f(0.15,0.15,0.2)
    draw_rounded_rect(bar_x, bar_y, bar_w, bar_h, r=6)
    pct = min(score/100.0, 1.0)
    # gradient fill
    glBegin(GL_QUADS)
    glColor3f(0.1,0.8,0.3); glVertex2f(bar_x, bar_y)
    glColor3f(0.4,1.0,0.2); glVertex2f(bar_x+bar_w*pct, bar_y)
    glColor3f(0.3,0.9,0.1); glVertex2f(bar_x+bar_w*pct, bar_y+bar_h)
    glColor3f(0.05,0.6,0.2); glVertex2f(bar_x, bar_y+bar_h)
    glEnd()
    glColor3f(1,1,1)
    draw_text(bar_x+8, bar_y+12, f"Score: {int(score)} / 100")

    # --- Hearts ---
    for i in range(3):
        glColor3f((1.0,0.15,0.3)[0] if i<health else 0.3,
                  (0.15) if i<health else 0.1,
                  (0.3)  if i<health else 0.2)
        hx = WIN_W - 155 + i*48
        hy = WIN_H - 48
        r  = 9
        if i < health: glColor3f(1.0,0.15,0.35)
        else:          glColor3f(0.35,0.15,0.22)
        draw_circle_midpoint(hx+r,    hy+r, r, filled=True)
        draw_circle_midpoint(hx+r*3,  hy+r, r, filled=True)
        glBegin(GL_TRIANGLES)
        glVertex2f(hx,       hy+r)
        glVertex2f(hx+r*4,   hy+r)
        glVertex2f(hx+r*2,   hy)
        glEnd()

    # --- Speed badge ---
    glColor4f(0,0,0,0.5)
    draw_rounded_rect(WIN_W-125, 8, 115, 28, r=6)
    glColor3f(1,0.85,0.2)
    draw_text(WIN_W-118, 16, f"Speed: {speed_mult:.1f}x", GLUT_BITMAP_HELVETICA_12)

# ============================================================
#  BUTTON HELPER
# ============================================================
def draw_button(x, y, w, h, label, hover=False, danger=False):
    if danger:
        bc = (0.7,0.1,0.1) if hover else (0.5,0.05,0.05)
    else:
        bc = (0.2,0.6,1.0) if hover else (0.1,0.35,0.75)
    glColor4f(*bc, 0.92)
    draw_rounded_rect(x, y, w, h, r=10)
    glColor4f(1,1,1,0.15)
    draw_rounded_rect(x+2, y+h//2, w-4, h//2-2, r=8)  # shine
    glColor3f(1,1,1)
    tw = len(label) * 9
    draw_text(x + w//2 - tw//2, y + h//2 - 6, label, GLUT_BITMAP_HELVETICA_18)

# ============================================================
#  RENDER FUNCTIONS
# ============================================================

# ---- STORY ----
def render_story():
    global story_idx, story_char, story_hold, story_done
    global kidnap_phase, kidnap_car, kidnap_girl, kidnap_timer, current_state

    # Background
    draw_sky()
    draw_stars()
    draw_mountains()
    draw_clouds()
    draw_birds()
    draw_ground()

    # ---- Kidnap cinematic (runs AFTER typewriter finishes) ----
    if kidnap_phase > 0:
        kidnap_timer += 1

        if kidnap_phase == 1:
            # Boy stands on left, girl stands still, black car enters from left
            # Draw boy (static)
            glPushMatrix()
            px_save, py_save = player.x, player.y
            player.x, player.y = WIN_W//2 - 140, GROUND_Y
            player.draw()
            player.x, player.y = px_save, py_save
            glPopMatrix()

            # Draw girl standing still
            kidnap_girl.draw()

            # Car accelerates in from the left
            kidnap_car.spd = min(kidnap_car.spd + 0.4, 12)
            kidnap_car.x  += kidnap_car.spd
            kidnap_car.draw()

            if kidnap_car.x > WIN_W//2 - 60:
                kidnap_phase  = 2
                kidnap_timer  = 0

        elif kidnap_phase == 2:
            # Car stopped next to girl — girl is inside
            glPushMatrix()
            px_save, py_save = player.x, player.y
            player.x, player.y = WIN_W//2 - 140, GROUND_Y
            player.draw()
            player.x, player.y = px_save, py_save
            glPopMatrix()

            kidnap_car.draw()   # girl is now inside the car (not drawn separately)

            # Flash text
            pulse = abs(math.sin(kidnap_timer * 0.1))
            glColor3f(1, pulse * 0.4 + 0.6, 0.1)
            draw_text_large(WIN_W//2 - 80, GROUND_Y + 130, "SHE'S BEEN TAKEN!")
            glColor3f(0.9, 0.7, 0.7)
            draw_text(WIN_W//2 - 115, GROUND_Y + 95, "A black car sped away with her!", GLUT_BITMAP_HELVETICA_18)

            # Boy reaction — shock
            glColor3f(1, 0.9, 0.1)
            draw_text_large(WIN_W//2 - 190, GROUND_Y + 175, "The boy is DETERMINED.")

            if kidnap_timer > 140:
                kidnap_phase = 3
                kidnap_timer = 0

        elif kidnap_phase == 3:
            # Car accelerates away to the right
            glPushMatrix()
            px_save, py_save = player.x, player.y
            player.x, player.y = WIN_W//2 - 140, GROUND_Y
            player.draw()
            player.x, player.y = px_save, py_save
            glPopMatrix()

            kidnap_car.spd = min(kidnap_car.spd + 0.7, 22)
            kidnap_car.x  += kidnap_car.spd
            kidnap_car.draw()
            emit_smoke(kidnap_car.x, kidnap_car.y + 20)

            glColor3f(0.9, 0.3, 0.3)
            draw_text_large(WIN_W//2 - 160, WIN_H//2 + 80, "THE RESCUE MISSION BEGINS!")

            if kidnap_car.x > WIN_W + 200:
                kidnap_phase = 4

        elif kidnap_phase == 4:
            # Trigger fade directly to GAME — only once
            if not story_done:
                story_done = True
                _start_new_game()   # auto-starts the game after kidnap cinematic

        return  # skip typewriter rendering during kidnap

    # ---- Typewriter phase: draw boy + girl standing together ----
    # Boy
    glPushMatrix()
    px_save, py_save = player.x, player.y
    player.x, player.y = WIN_W//2 - 110, GROUND_Y
    player.draw()
    player.x, player.y = px_save, py_save
    glPopMatrix()
    # Girl — only visible during typewriter (before kidnap starts)
    Girl(WIN_W//2 + 30, GROUND_Y).draw()

    # ---- Text box ----
    glColor4f(0, 0, 0, 0.58)
    draw_rounded_rect(60, WIN_H - 248, WIN_W - 120, 165, r=14)
    # Decorative border
    glColor4f(0.6, 0.4, 0.8, 0.5)
    glLineWidth(2)
    draw_rect_outline(62, WIN_H - 246, WIN_W - 124, 161)
    glLineWidth(1)

    if story_idx < len(story_lines):
        line    = story_lines[story_idx]
        visible = line[:int(story_char)]
        glColor3f(0.95, 0.9, 1.0)
        tw = len(visible) * 13
        draw_text_large(WIN_W//2 - tw//2, WIN_H - 175, visible)

        # Progress dots
        glColor3f(0.5, 0.5, 0.7)
        draw_text(WIN_W//2 - 40, WIN_H - 215, f"{story_idx+1} / {len(story_lines)}",
                  GLUT_BITMAP_HELVETICA_12)

        story_char += STORY_SPEED
        if story_char >= len(line):
            story_hold += 1
            story_char  = float(len(line))
            if story_hold >= HOLD_FRAMES:
                advance_story()
    else:
        # All lines done — start kidnap if not already
        if kidnap_phase == 0:
            kidnap_phase = 1
            kidnap_car   = KidnapperCar(-150, direction=1)
            kidnap_car.spd = 0
            kidnap_girl  = Girl(WIN_W//2 + 30, GROUND_Y)  # same position as story girl

    glColor3f(0.5, 0.6, 0.5)
    draw_text(WIN_W//2 - 70, 28, "SPACE to skip story", GLUT_BITMAP_HELVETICA_12)

# ---- MENU ----
# Menu items: Story | Resume (if game_started) | Restart | Exit
# menu_selected indexes into the visible list
def _menu_items():
    """Return list of (label, action) tuples based on game state."""
    items = [("Story", "story")]
    if game_started:
        items.append(("Resume", "resume"))
    items.append(("Restart", "restart"))
    items.append(("Exit",    "exit"))
    return items

def render_menu():
    global menu_selected
    items = _menu_items()
    # clamp selection
    if menu_selected >= len(items):
        menu_selected = len(items) - 1

    # Animated BG
    draw_sky()
    draw_stars()
    draw_mountains()
    draw_clouds()
    draw_birds()
    draw_ground()

    # Panel
    panel_h = 80 + len(items) * 62 + 100
    panel_y = WIN_H//2 - panel_h//2
    glColor4f(0.02, 0.02, 0.10, 0.82)
    draw_rounded_rect(WIN_W//2 - 250, panel_y, 500, panel_h, r=22)
    glColor4f(0.35, 0.3, 0.9, 0.18)
    draw_rounded_rect(WIN_W//2 - 248, panel_y + panel_h//2, 496, panel_h//2 - 4, r=18)

    # Title
    glColor3f(1.0, 0.85, 0.2)
    draw_text_large(WIN_W//2 - 120, panel_y + panel_h - 46, "LOVE  RESCUE")
    glColor3f(0.9, 0.5, 0.7)
    draw_text(WIN_W//2 - 108, panel_y + panel_h - 70,
              "A Computer Graphics Adventure", GLUT_BITMAP_HELVETICA_12)

    # Pulsing heart
    pulse = 0.85 + 0.15 * math.sin(frame_count * 0.08)
    glPushMatrix()
    glTranslatef(WIN_W//2, panel_y + panel_h - 22, 0)
    glScalef(pulse, pulse, 1)
    glColor3f(1, 0.15, 0.35)
    draw_circle_midpoint(-10, 0, 10, filled=True)
    draw_circle_midpoint( 10, 0, 10, filled=True)
    glBegin(GL_TRIANGLES)
    glVertex2f(-20, 0); glVertex2f(20, 0); glVertex2f(0, -20)
    glEnd()
    glPopMatrix()

    # Buttons
    btn_w, btn_h = 240, 50
    bx = WIN_W//2 - btn_w//2
    for i, (lbl, act) in enumerate(items):
        by = panel_y + panel_h - 110 - i * 62
        danger = (act == "exit")
        draw_button(bx, by, btn_w, btn_h, lbl,
                    hover=(menu_selected == i), danger=danger)

    glColor3f(0.5, 0.55, 0.6)
    draw_text(WIN_W//2 - 100, panel_y + 14,
              "UP/DOWN to navigate  |  ENTER to select",
              GLUT_BITMAP_HELVETICA_12)

# ---- GAME ----
def render_game():
    draw_sky()
    draw_stars()
    draw_mountains()
    draw_clouds()
    draw_birds()
    draw_ground()

    # Obstacles
    for obs in obstacles:
        obs.draw()

    # Particles
    for pt in particles:
        pt.draw()

    # Player
    player.draw()

    # HUD
    draw_hud()

    # Screen shake
    if player.shake > 0:
        pass  # shake handled in display via glTranslate

# ---- PAUSED ----
def render_paused():
    render_game()
    glColor4f(0,0,0,0.5)
    draw_rect_filled(0,0,WIN_W,WIN_H)
    glColor3f(1,0.85,0.2)
    draw_text_large(WIN_W//2 - 80, WIN_H//2 + 30, "PAUSED")
    glColor3f(0.9,0.9,0.9)
    draw_text(WIN_W//2 - 90, WIN_H//2 - 20, "P - Resume     R - Restart     ESC - Menu",
              GLUT_BITMAP_HELVETICA_18)

# ---- GAME OVER ----
def render_gameover():
    draw_sky()
    draw_mountains()
    draw_ground()
    for pt in particles: pt.draw()

    glColor4f(0,0,0,0.65)
    draw_rounded_rect(WIN_W//2 - 280, WIN_H//2 - 180, 560, 380, r=20)

    glColor3f(1.0, 0.15, 0.15)
    draw_text_large(WIN_W//2 - 105, WIN_H//2 + 140, "GAME  OVER")
    glColor3f(0.9, 0.7, 0.7)
    draw_text(WIN_W//2 - 140, WIN_H//2 + 95, "You couldn't rescue your love...", GLUT_BITMAP_HELVETICA_18)
    glColor3f(0.6,0.6,0.7)
    draw_text(WIN_W//2 - 60, WIN_H//2 + 65, f"Final Score: {int(score)}", GLUT_BITMAP_HELVETICA_18)

    btn_w, btn_h = 200, 46
    bx = WIN_W//2 - btn_w//2
    draw_button(bx, WIN_H//2 - 20,  btn_w, btn_h, "Retry",     hover=True)
    draw_button(bx, WIN_H//2 - 80,  btn_w, btn_h, "Main Menu")
    draw_button(bx, WIN_H//2 - 140, btn_w, btn_h, "Exit",      danger=True)

    draw_text(WIN_W//2-100, WIN_H//2-188,
              "Click a button or press R / M / ESC", GLUT_BITMAP_HELVETICA_12)

# ---- WIN night-sky background helpers ----
# Pre-generate a rich star field just for the win scene
_win_stars = [
    (random.uniform(0, WIN_W), random.uniform(GROUND_Y + 20, WIN_H),
     random.uniform(0.8, 3.0),
     (random.random(), random.uniform(0.7,1.0), random.uniform(0.7,1.0)))   # hue-ish colour
    for _ in range(200)
]
# Coloured sparkle/lantern seeds
_sparkle_colors = [
    (1.0, 0.3, 0.5),   # pink
    (0.4, 0.8, 1.0),   # cyan
    (1.0, 0.9, 0.3),   # gold
    (0.7, 0.35, 1.0),  # purple
    (0.3, 1.0, 0.6),   # mint
    (1.0, 0.55, 0.1),  # orange
]

def draw_win_night_sky():
    """Deep romantic night sky gradient."""
    glBegin(GL_QUADS)
    glColor3f(0.0,  0.0,  0.06);  glVertex2f(0,       GROUND_Y)
    glColor3f(0.0,  0.0,  0.06);  glVertex2f(WIN_W,   GROUND_Y)
    glColor3f(0.02, 0.0,  0.15);  glVertex2f(WIN_W,   WIN_H * 0.55)
    glColor3f(0.02, 0.0,  0.15);  glVertex2f(0,       WIN_H * 0.55)
    glEnd()
    glBegin(GL_QUADS)
    glColor3f(0.02, 0.0,  0.15);  glVertex2f(0,       WIN_H * 0.55)
    glColor3f(0.02, 0.0,  0.15);  glVertex2f(WIN_W,   WIN_H * 0.55)
    glColor3f(0.04, 0.01, 0.22);  glVertex2f(WIN_W,   WIN_H)
    glColor3f(0.04, 0.01, 0.22);  glVertex2f(0,       WIN_H)
    glEnd()

def draw_win_aurora():
    """Soft coloured aurora bands sweeping across the upper sky."""
    t = frame_count * 0.012
    bands = [
        (WIN_H * 0.80, 60, (0.2, 0.6, 1.0, 0.07)),
        (WIN_H * 0.72, 45, (0.5, 0.2, 0.9, 0.06)),
        (WIN_H * 0.88, 55, (0.1, 0.8, 0.6, 0.05)),
    ]
    for (base_y, amplitude, col) in bands:
        glEnable(GL_BLEND)
        glColor4f(*col)
        glBegin(GL_QUADS)
        for xi in range(0, WIN_W, 40):
            wave  = math.sin(t + xi * 0.015) * amplitude
            wave2 = math.sin(t + xi * 0.015 + 0.8) * amplitude
            glVertex2f(xi,      base_y + wave)
            glVertex2f(xi + 40, base_y + wave2)
            glVertex2f(xi + 40, base_y + wave2 + 28)
            glVertex2f(xi,      base_y + wave  + 28)
        glEnd()

def draw_win_stars():
    """200 twinkling coloured stars."""
    for sx, sy, sz, col in _win_stars:
        twinkle = 0.55 + 0.45 * math.sin(frame_count * 0.07 + sx * 0.03 + sy * 0.02)
        glEnable(GL_BLEND)
        glPointSize(sz * twinkle + 0.5)
        glColor4f(col[0], col[1], col[2], twinkle)
        glBegin(GL_POINTS); glVertex2f(sx, sy); glEnd()

def draw_sparkle_burst(cx, cy, r, col, angle_offset=0):
    """8-point star sparkle."""
    glColor4f(*col)
    glLineWidth(1.5)
    glBegin(GL_LINES)
    for i in range(8):
        a  = math.radians(i * 45 + angle_offset)
        r2 = r * (0.4 if i % 2 == 0 else 1.0)
        glVertex2f(cx, cy)
        glVertex2f(cx + math.cos(a) * r2, cy + math.sin(a) * r2)
    glEnd()
    glLineWidth(1.0)

def draw_win_sparkles():
    """Rotating coloured sparkles scattered across the sky."""
    for i, col in enumerate(_sparkle_colors):
        # Each sparkle orbits a fixed point, slowly
        ox = 100 + i * (WIN_W - 200) // (len(_sparkle_colors) - 1)
        oy = WIN_H * 0.55 + math.sin(i * 1.1) * 80
        angle = (frame_count * (1.5 + i * 0.3)) % 360
        alpha = 0.55 + 0.45 * math.sin(frame_count * 0.05 + i * 1.2)
        draw_sparkle_burst(ox, oy, 18 + 6 * math.sin(frame_count*0.08+i),
                           (*col, alpha), angle_offset=angle)
        # Small halo circle
        glColor4f(*col, alpha * 0.25)
        draw_circle_midpoint(int(ox), int(oy), 22, filled=True)

def emit_win_lantern():
    """Floating golden lantern particle."""
    x = random.randint(80, WIN_W - 80)
    col = random.choice(_sparkle_colors)
    particles.append(Particle(x, GROUND_Y + 10,
        random.uniform(-0.4, 0.4), random.uniform(1.0, 2.2),
        (*col, 0.85), random.randint(180, 280), size=5, gravity=False))

# ---- WIN scene ----
win_girl = None
def render_win():
    global win_timer, win_phase, win_girl, firework_timer

    # ===== Beautiful night background =====
    draw_win_night_sky()
    draw_win_aurora()
    draw_win_stars()
    draw_win_sparkles()

    # Night ground
    glColor3f(0.06, 0.05, 0.12)
    draw_rect_filled(0, 0, WIN_W, GROUND_Y)
    # Ground glow strip
    glBegin(GL_QUADS)
    glColor4f(0.5, 0.2, 0.8, 0.18); glVertex2f(0,     GROUND_Y)
    glColor4f(0.5, 0.2, 0.8, 0.18); glVertex2f(WIN_W, GROUND_Y)
    glColor4f(0.0, 0.0, 0.0, 0.0);  glVertex2f(WIN_W, GROUND_Y - 30)
    glColor4f(0.0, 0.0, 0.0, 0.0);  glVertex2f(0,     GROUND_Y - 30)
    glEnd()

    win_timer += 1

    # Emit floating lanterns occasionally
    if frame_count % 22 == 0:
        emit_win_lantern()

    # ------- Phase 0: girl runs toward boy -------
    if win_phase == 0:
        if win_girl is None:
            win_girl = Girl(WIN_W + 80, GROUND_Y)
        win_girl.x -= 4.5
        win_girl.draw(run=True)

        # Boy waits at center-left
        glPushMatrix()
        px_save, py_save = player.x, player.y
        player.x, player.y = WIN_W//2 - 60, GROUND_Y
        player.draw()
        player.x, player.y = px_save, py_save
        glPopMatrix()

        glColor3f(1, 0.9, 0.3)
        draw_text_large(WIN_W//2 - 130, WIN_H - 78, "You saved her!")

        # Girl stops right next to boy (gap = ~40 px)
        if win_girl.x < WIN_W//2 + 40:
            win_phase = 1
            win_timer = 0
            for _ in range(8):
                emit_hearts(WIN_W//2, GROUND_Y + 110)

    # ------- Phase 1 & 2: close romantic scene -------
    else:
        # Boy and girl stand close together — shoulder gap ~38 px
        boy_x  = WIN_W//2 - 55   # boy's left edge
        girl_x = WIN_W//2 + 20   # girl's left edge  (gap ≈ boy_x+32+6 = 38px)

        # Soft glow under them
        glColor4f(1.0, 0.4, 0.7, 0.10)
        draw_ellipse_midpoint(WIN_W//2, GROUND_Y + 4, 80, 14, filled=True)

        # Draw boy
        glPushMatrix()
        px_save, py_save = player.x, player.y
        player.x, player.y = boy_x, GROUND_Y
        player.draw()
        player.x, player.y = px_save, py_save
        glPopMatrix()

        # Draw girl (facing boy — she's on right so she faces left naturally)
        if win_girl:
            win_girl.x = girl_x
            win_girl.y = GROUND_Y
            win_girl.draw()

        # --- Pulsing heart floating just above their heads ---
        heart_cx = WIN_W//2 + 8     # slightly right of center (between the two)
        heart_cy = GROUND_Y + 130
        pulse    = 0.88 + 0.12 * math.sin(frame_count * 0.11)
        hr       = int(22 * pulse)

        glPushMatrix()
        glTranslatef(heart_cx, heart_cy, 0)
        glScalef(pulse, pulse, 1.0)
        # Glow
        glColor4f(1.0, 0.35, 0.6, 0.22)
        draw_circle_midpoint(-hr, hr//2, hr+8, filled=True)
        draw_circle_midpoint( hr, hr//2, hr+8, filled=True)
        # Solid heart
        glColor3f(1.0, 0.12, 0.35)
        draw_circle_midpoint(-hr//2,  hr//2, hr, filled=True)
        draw_circle_midpoint( hr//2,  hr//2, hr, filled=True)
        glBegin(GL_TRIANGLES)
        glVertex2f(-hr, hr//2); glVertex2f(hr, hr//2); glVertex2f(0, -hr)
        glEnd()
        # Shine
        glColor4f(1.0, 0.85, 0.9, 0.6)
        draw_circle_midpoint(-hr//4, hr//2 + 3, hr//4, filled=True)
        glPopMatrix()

        # Floating hearts around them
        if frame_count % 9 == 0:
            emit_hearts(WIN_W//2 + random.randint(-70, 70),
                        GROUND_Y + random.randint(80, 150))

        # Romantic text panel
        glColor4f(0.0, 0.0, 0.08, 0.55)
        draw_rounded_rect(WIN_W//2 - 260, WIN_H - 140, 520, 70, r=14)

        glColor3f(1.0, 0.3, 0.55)
        draw_text_large(WIN_W//2 - 168, WIN_H - 88, "CONGRATULATIONS!")
        glColor3f(1.0, 0.82, 0.88)
        draw_text(WIN_W//2 - 185, WIN_H - 118,
                  "You Finally Rescued Your Love  <3",
                  GLUT_BITMAP_HELVETICA_18)

        if win_phase == 2:
            # Fireworks
            firework_timer += 1
            if firework_timer % 22 == 0:
                emit_firework(random.randint(60, WIN_W - 60),
                              random.randint(260, WIN_H - 40))
            # Confetti
            if frame_count % 3 == 0:
                for _ in range(5):
                    emit_confetti(random.randint(0, WIN_W), WIN_H)

            # Buttons
            btn_w, btn_h = 190, 46
            draw_button(WIN_W//2 - 295, 28, btn_w, btn_h, "Play Again", hover=True)
            draw_button(WIN_W//2 -  90, 28, btn_w, btn_h, "Main Menu")
            draw_button(WIN_W//2 + 115, 28, btn_w, btn_h, "Exit", danger=True)

        if win_phase == 1 and win_timer > 100:
            win_phase      = 2
            firework_timer = 0

    for pt in particles: pt.draw()


# ============================================================
#  MAIN DISPLAY CALLBACK
# ============================================================
def display():
    global frame_count, fade_alpha, fading_in, fade_done

    frame_count += 1

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Screen shake
    sx, sy = 0, 0
    if current_state == STATE_GAME and player.shake > 0:
        sx = random.uniform(-4,4)
        sy = random.uniform(-3,3)
        player.shake -= 1
    glTranslatef(sx, sy, 0)

    if   current_state == STATE_STORY:    render_story()
    elif current_state == STATE_MENU:     render_menu()
    elif current_state == STATE_GAME:     render_game()
    elif current_state == STATE_PAUSED:   render_paused()
    elif current_state == STATE_GAMEOVER: render_gameover()
    elif current_state == STATE_WIN:      render_win()

    # Fade overlay
    if not fade_done:
        if fading_in:
            fade_alpha = max(0.0, fade_alpha - 0.025)
            draw_overlay(fade_alpha)
            if fade_alpha <= 0: fading_in = False; fade_done = True
        else:
            fade_alpha = min(1.0, fade_alpha + 0.025)
            draw_overlay(fade_alpha)
            if fade_alpha >= 1.0: fading_in = True; fade_done = False

    glutSwapBuffers()

def start_fade_out(callback_state):
    """Begin fade-out then switch state."""
    global fade_alpha, fading_in, fade_done, _pending_state
    fade_done       = False
    fading_in       = False
    fade_alpha      = 0.0
    _pending_state  = callback_state

_pending_state = None

# ============================================================
#  UPDATE (TIMER)
# ============================================================
def update(value):
    global current_state, score, speed_mult, spawn_timer, spawn_delay
    global health, fade_alpha, fading_in, fade_done, _pending_state

    # Handle fade transition
    if _pending_state is not None and fade_alpha >= 1.0:
        current_state  = _pending_state
        _pending_state = None
        fade_done      = False
        fading_in      = True

    update_background(speed_mult if current_state == STATE_GAME else 0.5)

    if current_state == STATE_GAME:
        player.update()
        # Score increases slowly; speed ramps up gently (÷150 instead of ÷55)
        score      += 0.05 * speed_mult
        speed_mult  = 1.0 + score / 150.0

        # Spawn obstacles
        spawn_timer += 1
        spawn_delay  = max(45, int(110 / speed_mult))
        if spawn_timer >= spawn_delay:
            spawn_timer = 0
            cls = random.choice(OBSTACLE_CLASSES)
            obstacles.append(cls(WIN_W + 20))

        # Update obstacles + collision
        for obs in obstacles[:]:
            obs.update(speed_mult)
            px1,py1,px2,py2 = player.get_aabb()
            ox1,oy1,ox2,oy2 = obs.get_aabb()
            if aabb_check(px1,py1,px2,py2, ox1,oy1,ox2,oy2):
                player.hit()
                obstacles.remove(obs)
                continue
            if obs.x + getattr(obs,'w', getattr(obs,'r',50)*2) < -30:
                obstacles.remove(obs)

        health = player.health
        # Death → go to Game Over immediately (no fade delay)
        if not player.alive:
            current_state = STATE_GAMEOVER

        # Win → stop the game immediately when score hits 100
        if score >= 100:
            score = 100.0          # cap it cleanly
            current_state = STATE_WIN
            # seed the win scene
            global win_girl
            win_girl = None

    # Update particles
    particles[:] = [p for p in particles if p.update()]

    glutPostRedisplay()
    glutTimerFunc(1000 // FPS, update, 0)

# ============================================================
#  INPUT
# ============================================================
def keyboard(key, x, y):
    global current_state, menu_selected, story_idx, story_char, kidnap_phase, kidnap_car, kidnap_girl

    try:
        k = key.decode("utf-8").lower()
    except:
        k = ""

    if k == '\x1b':   # ESC
        if current_state == STATE_GAME:
            current_state = STATE_MENU
        elif current_state == STATE_PAUSED:
            current_state = STATE_MENU
        elif current_state in (STATE_GAMEOVER, STATE_WIN):
            current_state = STATE_MENU
        else:
            os._exit(0)

    elif k == '\r' or k == '\n':   # ENTER
        if current_state == STATE_MENU:
            items = _menu_items()
            if menu_selected < len(items):
                act = items[menu_selected][1]
                if   act == "story":   _go_story()
                elif act == "resume":  current_state = STATE_GAME
                elif act == "restart": _start_new_game()
                elif act == "exit":    os._exit(0)

    elif k == ' ':
        if current_state == STATE_STORY:
            # Skip straight to kidnap cinematic
            if kidnap_phase == 0:
                story_idx    = len(story_lines)
                story_char   = 0.0
                story_hold   = 0
                kidnap_phase = 1
                kidnap_car   = KidnapperCar(-150, direction=1)
                kidnap_car.spd = 0
                kidnap_girl  = Girl(WIN_W//2 + 30, GROUND_Y)
        elif current_state == STATE_GAME:
            player.jump()

    elif k == 'p':
        if current_state == STATE_GAME:
            current_state = STATE_PAUSED
        elif current_state == STATE_PAUSED:
            current_state = STATE_GAME

    elif k == 'r':
        if current_state in (STATE_GAMEOVER, STATE_WIN, STATE_PAUSED):
            _start_new_game()
        elif current_state == STATE_GAME:
            _start_new_game()

    elif k == 'm':
        current_state = STATE_MENU

    elif k == 's':
        if current_state == STATE_GAME:
            player.sliding = True

def keyboard_up(key, x, y):
    try: k = key.decode("utf-8").lower()
    except: k = ""
    if k == 's':
        player.sliding = False

def special_keys(key, x, y):
    global menu_selected
    if current_state == STATE_GAME:
        if key == GLUT_KEY_UP:
            player.jump()
        elif key == GLUT_KEY_DOWN:
            player.sliding = True
        elif key == GLUT_KEY_LEFT:
            player.x = max(10, player.x - 20)
        elif key == GLUT_KEY_RIGHT:
            player.x = min(WIN_W//2, player.x + 20)
    elif current_state == STATE_MENU:
        n = len(_menu_items())
        if key == GLUT_KEY_UP:
            menu_selected = (menu_selected - 1) % n
        elif key == GLUT_KEY_DOWN:
            menu_selected = (menu_selected + 1) % n

def special_keys_up(key, x, y):
    if key == GLUT_KEY_DOWN:
        player.sliding = False

# ============================================================
#  MOUSE
# ============================================================
def mouse(button, state, mx, my):
    global current_state
    if button != GLUT_LEFT_BUTTON or state != GLUT_UP:
        return
    my = WIN_H - my   # flip y

    if current_state == STATE_GAMEOVER:
        btn_w, btn_h = 200, 46
        bx = WIN_W//2 - btn_w//2
        if _in_btn(mx, my, bx, WIN_H//2 - 20,  btn_w, btn_h): _start_new_game()
        if _in_btn(mx, my, bx, WIN_H//2 - 80,  btn_w, btn_h): current_state = STATE_MENU
        if _in_btn(mx, my, bx, WIN_H//2 - 140, btn_w, btn_h): os._exit(0)

    elif current_state == STATE_WIN and win_phase == 2:
        btn_w, btn_h = 190, 46
        if _in_btn(mx, my, WIN_W//2 - 295, 30, btn_w, btn_h): _start_new_game()
        if _in_btn(mx, my, WIN_W//2 -  90, 30, btn_w, btn_h): current_state = STATE_MENU
        if _in_btn(mx, my, WIN_W//2 + 115, 30, btn_w, btn_h): os._exit(0)

    elif current_state == STATE_MENU:
        items   = _menu_items()
        btn_w, btn_h = 240, 50
        bx = WIN_W//2 - btn_w//2
        panel_h = 80 + len(items)*62 + 100
        panel_y = WIN_H//2 - panel_h//2
        for i, (lbl, act) in enumerate(items):
            by = panel_y + panel_h - 110 - i*62
            if _in_btn(mx, my, bx, by, btn_w, btn_h):
                if   act == "story":   _go_story()
                elif act == "resume":  current_state = STATE_GAME
                elif act == "restart": _start_new_game()
                elif act == "exit":    os._exit(0)
                break

def _in_btn(mx, my, bx, by, bw, bh):
    return bx <= mx <= bx+bw and by <= my <= by+bh

def _start_new_game():
    global current_state, fade_alpha, fading_in, fade_done, win_girl, game_started
    win_girl      = None
    game_started  = True
    reset_game()
    fade_done     = False
    fading_in     = True
    fade_alpha    = 1.0
    current_state = STATE_GAME

def _go_story():
    global current_state, story_idx, story_char, story_hold, kidnap_phase
    global kidnap_car, kidnap_girl, story_done, fade_done, fading_in, fade_alpha
    story_idx     = 0
    story_char    = 0.0
    story_hold    = 0
    kidnap_phase  = 0
    kidnap_car    = None
    kidnap_girl   = None
    story_done    = False
    fade_done     = False
    fading_in     = True
    fade_alpha    = 1.0
    current_state = STATE_STORY

# ============================================================
#  OPENGL INIT
# ============================================================
def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, WIN_W, 0.0, WIN_H, -1.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def init_gl():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_POINT_SMOOTH)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glPointSize(2.0)

# ============================================================
#  MAIN
# ============================================================
if __name__ == "__main__":
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(100, 60)
    glutCreateWindow(b"Love Rescue  -  A Computer Graphics Game")

    init_gl()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_keys)
    glutSpecialUpFunc(special_keys_up)
    glutMouseFunc(mouse)
    glutTimerFunc(1000 // FPS, update, 0)

    print("=" * 50)
    print("  LOVE RESCUE  -  Controls:")
    print("  UP / SPACE   : Jump")
    print("  DOWN / S     : Slide")
    print("  LEFT / RIGHT : Move horizontally")
    print("  P            : Pause")
    print("  R            : Restart")
    print("  M            : Main Menu")
    print("  ESC          : Back / Exit")
    print("  ENTER        : Select menu item")
    print("=" * 50)

    glutMainLoop()
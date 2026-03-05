from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random

# Game Settings
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# Game State Variables
paddle_w, paddle_h = 15, 100
p1_y, p2_y = 250.0, 250.0 # Left and right paddle Y positions
paddle_speed = 8.0

ball_x, ball_y = 400.0, 300.0
ball_size = 12
ball_dx, ball_dy = 5.0, 5.0

score1, score2 = 0, 0

# Dictionary to track which keys are currently being pressed down
key_states = {'w': False, 's': False, 'UP': False, 'DOWN': False}

def draw_rect(x, y, width, height):
    """Draws a solid rectangle."""
    glBegin(GL_QUADS)
    glVertex2f(x, y)
    glVertex2f(x + width, y)
    glVertex2f(x + width, y + height)
    glVertex2f(x, y + height)
    glEnd()

def draw_text(text, x, y):
    """Draws a string of text on the screen."""
    glRasterPos2f(x, y)
    for character in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(character))

def reset_ball():
    """Puts the ball back in the center and sends it in a random direction."""
    global ball_x, ball_y, ball_dx, ball_dy
    ball_x, ball_y = WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2
    # Randomize starting direction
    ball_dx = 5.0 if random.choice([True, False]) else -5.0
    ball_dy = random.uniform(-4.0, 4.0)

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    
    # Draw center dashed line
    glColor3f(0.3, 0.3, 0.3)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    for y in range(0, WINDOW_HEIGHT, 30):
        glVertex2f(WINDOW_WIDTH / 2, y)
        glVertex2f(WINDOW_WIDTH / 2, y + 15)
    glEnd()

    glColor3f(1.0, 1.0, 1.0) # White color for game objects
    
    # Draw Paddles
    draw_rect(30, p1_y, paddle_w, paddle_h) # Player 1 (Left)
    draw_rect(WINDOW_WIDTH - 30 - paddle_w, p2_y, paddle_w, paddle_h) # Player 2 (Right)
    
    # Draw Ball
    draw_rect(ball_x, ball_y, ball_size, ball_size)
    
    # Draw Scores
    draw_text(str(score1), WINDOW_WIDTH / 4, WINDOW_HEIGHT - 50)
    draw_text(str(score2), WINDOW_WIDTH * 3 / 4, WINDOW_HEIGHT - 50)
    
    glutSwapBuffers()

def update(value):
    """Main game loop handling movement and collisions."""
    global p1_y, p2_y, ball_x, ball_y, ball_dx, ball_dy, score1, score2
    
    # --- 1. Paddle Movement ---
    if key_states['w'] and p1_y < WINDOW_HEIGHT - paddle_h:
        p1_y += paddle_speed
    if key_states['s'] and p1_y > 0:
        p1_y -= paddle_speed
        
    if key_states['UP'] and p2_y < WINDOW_HEIGHT - paddle_h:
        p2_y += paddle_speed
    if key_states['DOWN'] and p2_y > 0:
        p2_y -= paddle_speed

    # --- 2. Ball Movement ---
    ball_x += ball_dx
    ball_y += ball_dy

    # --- 3. Wall Collisions (Top & Bottom) ---
    if ball_y <= 0 or ball_y + ball_size >= WINDOW_HEIGHT:
        ball_dy = -ball_dy # Reverse Y direction

    # --- 4. Paddle Collisions ---
    # Left Paddle Collision
    if (30 <= ball_x <= 30 + paddle_w) and (p1_y <= ball_y + ball_size and ball_y <= p1_y + paddle_h):
        ball_dx = abs(ball_dx) + 0.5 # Bounce right and slightly speed up
        
    # Right Paddle Collision
    if (WINDOW_WIDTH - 30 - paddle_w <= ball_x + ball_size <= WINDOW_WIDTH - 30) and \
       (p2_y <= ball_y + ball_size and ball_y <= p2_y + paddle_h):
        ball_dx = -abs(ball_dx) - 0.5 # Bounce left and slightly speed up

    # --- 5. Scoring ---
    if ball_x < 0:
        score2 += 1
        reset_ball()
    elif ball_x > WINDOW_WIDTH:
        score1 += 1
        reset_ball()

    glutPostRedisplay()
    glutTimerFunc(16, update, 0) # ~60 FPS (1000ms / 60 ≈ 16ms)

# --- Input Handling ---
# We track "Key Down" and "Key Up" separately to allow smooth, simultaneous movement
def keyboard_down(key, x, y):
    if key == b'w': key_states['w'] = True
    if key == b's': key_states['s'] = True

def keyboard_up(key, x, y):
    if key == b'w': key_states['w'] = False
    if key == b's': key_states['s'] = False

def special_down(key, x, y):
    if key == GLUT_KEY_UP: key_states['UP'] = True
    if key == GLUT_KEY_DOWN: key_states['DOWN'] = True

def special_up(key, x, y):
    if key == GLUT_KEY_UP: key_states['UP'] = False
    if key == GLUT_KEY_DOWN: key_states['DOWN'] = False

def init():
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Setup orthographic projection to map exactly to pixel coordinates
    glOrtho(0.0, WINDOW_WIDTH, 0.0, WINDOW_HEIGHT, -1.0, 1.0)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"PyOpenGL Pong")
    
    init()
    reset_ball()
    
    # Callbacks
    glutDisplayFunc(display)
    
    # Keyboard setup
    glutKeyboardFunc(keyboard_down)
    glutKeyboardUpFunc(keyboard_up)
    glutSpecialFunc(special_down)
    glutSpecialUpFunc(special_up)
    
    # Start game loop
    glutTimerFunc(16, update, 0)
    
    glutMainLoop()

if __name__ == "__main__":
    main()
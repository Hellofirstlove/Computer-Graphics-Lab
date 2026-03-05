from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random

# Global variables for animation state
tear_intensity = 0  # Ranges from 0 (no tears) to 10 (heavy crying)
tears = []          # List to hold individual tear drop data

def draw_circle(cx, cy, r, filled=True):
    """Helper function to draw circles for the face and eyes."""
    if filled:
        glBegin(GL_POLYGON)
    else:
        glBegin(GL_LINE_LOOP)
        
    for i in range(100):
        theta = 2.0 * math.pi * float(i) / 100.0
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        glVertex2f(x + cx, y + cy)
    glEnd()

def draw_face():
    """Draws the yellow face, black eyes, and a smile."""
    # Main Face (Yellow)
    glColor3f(1.0, 1.0, 0.0)
    draw_circle(0.5, 0.5, 0.3)
    
    # Left and Right Eyes (Black)
    glColor3f(0.0, 0.0, 0.0)
    draw_circle(0.4, 0.6, 0.03)
    draw_circle(0.6, 0.6, 0.03)
    
    # Smile (Black arc using line strip)
    glColor3f(0.0, 0.0, 0.0)
    glLineWidth(4.0)
    glBegin(GL_LINE_STRIP)
    # Ranging from 180 to 360 degrees draws the bottom half of a circle
    for i in range(180, 361):
        theta = i * math.pi / 180.0
        x = 0.15 * math.cos(theta)
        y = 0.15 * math.sin(theta)
        glVertex2f(x + 0.5, y + 0.5)
    glEnd()

def draw_tears():
    """Draws all active tear particles as small blue lines."""
    glColor3f(0.0, 0.7, 1.0)  # Light blue
    glLineWidth(2.0)
    glBegin(GL_LINES)
    for tear in tears:
        glVertex2f(tear['x'], tear['y'])
        # Draw a small trailing line upwards to simulate a falling drop
        glVertex2f(tear['x'], tear['y'] + 0.03)  
    glEnd()

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    
    draw_face()
    draw_tears()
    
    # Swap buffers instead of glFlush for smooth animation
    glutSwapBuffers()  

def update_tears(value):
    """Timer function to update tear positions and spawn new ones."""
    global tears, tear_intensity
    
    # Spawn new tears based on current intensity
    if tear_intensity > 0:
        # Higher intensity = higher chance of spawning a tear this frame
        if random.random() < (tear_intensity * 0.15):
            # Add tear slightly below the left eye
            tears.append({'x': 0.4 + random.uniform(-0.015, 0.015), 
                          'y': 0.55, 
                          'speed': random.uniform(0.01, 0.025)})
            # Add tear slightly below the right eye
            tears.append({'x': 0.6 + random.uniform(-0.015, 0.015), 
                          'y': 0.55, 
                          'speed': random.uniform(0.01, 0.025)})
    
    # Move existing tears downwards
    for tear in tears:
        tear['y'] -= tear['speed']
        
    # Clean up tears that have fallen off the screen to save memory
    tears = [t for t in tears if t['y'] > 0.0]
    
    glutPostRedisplay()
    glutTimerFunc(30, update_tears, 0)  # Call this function again in 30ms

def special_keys(key, x, y):
    """Handles the left and right arrow keys to control tear volume."""
    global tear_intensity
    if key == GLUT_KEY_RIGHT:
        # Increase tears, capped at max intensity of 10
        tear_intensity = min(10, tear_intensity + 1)
        print(f"Tears increasing! Intensity: {tear_intensity}/10")
    elif key == GLUT_KEY_LEFT:
        # Decrease tears, floored at 0
        tear_intensity = max(0, tear_intensity - 1)
        print(f"Tears decreasing. Intensity: {tear_intensity}/10")

def init():
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Coordinate system goes from 0 to 1 on both X and Y axes
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)

def main():
    glutInit()
    # Changed from GLUT_SINGLE to GLUT_DOUBLE for smooth animation
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB) 
    glutInitWindowSize(600, 600)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Animated Smiley with Tears")
    
    init()
    
    # Register callbacks
    glutDisplayFunc(display)
    glutSpecialFunc(special_keys)  # For the arrow keys
    glutTimerFunc(0, update_tears, 0) # Start the animation loop
    
    glutMainLoop()

if __name__ == "__main__":
    main()
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

# Global animation state
time_step = 0.0

def get_wave_height(x, t):
    """Calculates a smooth rolling river wave."""
    return 0.25 + 0.04 * math.sin(5.0 * x + t * 1.5)

def reshape(w, h):
    """Fixes the 'small corner' issue by updating the viewport to the full window size."""
    # Prevent a divide by zero if the window is too small
    if h == 0: h = 1
    
    # Set the viewport to cover the new window size
    glViewport(0, 0, w, h)
    
    # Reset the coordinate system to match the window
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
    glMatrixMode(GL_MODELVIEW)

def draw_sunset_sky():
    glBegin(GL_QUADS)
    glColor3f(0.2, 0.1, 0.3) # Top Purple
    glVertex2f(0.0, 1.0)
    glVertex2f(1.0, 1.0)
    glColor3f(1.0, 0.4, 0.2) # Bottom Orange
    glVertex2f(1.0, 0.0)
    glVertex2f(0.0, 0.0)
    glEnd()

def draw_sun():
    glColor3f(1.0, 0.8, 0.0)
    glBegin(GL_POLYGON)
    sun_x, sun_y = 0.7, 0.35
    radius = 0.12
    for i in range(100):
        theta = 2.0 * math.pi * i / 100
        glVertex2f(sun_x + radius * math.cos(theta), sun_y + radius * math.sin(theta))
    glEnd()

def draw_river():
    global time_step
    glColor4f(0.1, 0.1, 0.4, 1.0) 
    glBegin(GL_POLYGON)
    glVertex2f(1.0, 0.0)
    glVertex2f(0.0, 0.0)
    for i in range(101):
        x = i / 100.0
        y = get_wave_height(x, time_step)
        glVertex2f(x, y)
    glEnd()

def draw_boat():
    global time_step
    bx = 0.4 
    by = get_wave_height(bx, time_step)
    dx = 0.01
    slope = (get_wave_height(bx + dx, time_step) - get_wave_height(bx - dx, time_step)) / (2 * dx)
    angle = math.degrees(math.atan(slope))

    glPushMatrix()
    glTranslatef(bx, by, 0.0)
    glRotatef(angle, 0, 0, 1)

    # Hull Silhouette
    glColor3f(0.15, 0.1, 0.05)
    glBegin(GL_POLYGON)
    glVertex2f(-0.15, 0.0)
    glVertex2f(0.15, 0.0)
    glVertex2f(0.18, 0.08)
    glVertex2f(-0.18, 0.08)
    glEnd()

    # Mast
    glRectf(-0.005, 0.08, 0.005, 0.35)

    # Sail
    glColor3f(0.8, 0.5, 0.3) 
    glBegin(GL_TRIANGLES)
    glVertex2f(-0.01, 0.1)
    glVertex2f(-0.01, 0.32)
    glVertex2f(-0.14, 0.12)
    glEnd()

    glPopMatrix()

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()
    
    draw_sunset_sky()
    draw_sun()        
    draw_river()      
    draw_boat()       
    
    glutSwapBuffers()

def timer(v):
    global time_step
    time_step += 0.02
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)
    glutInitWindowSize(1000, 600)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Sunset River Voyage - Full View")
    
    # These two functions ensure the scene fills the window
    glutReshapeFunc(reshape)
    glutDisplayFunc(display)
    
    glutTimerFunc(0, timer, 0)
    glutMainLoop()

if __name__ == "__main__":
    main()
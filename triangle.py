from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

def draw_circle(cx, cy, r, segments=100):
    glBegin(GL_POLYGON)
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        glVertex2f(x, y)
    glEnd()

def display():
    glClear(GL_COLOR_BUFFER_BIT)

    glColor3f(0.0, 0.5, 1.0)  # Blue color
    draw_circle(0.5, 0.5, 0.3)  # center (0.5,0.5), radius 0.3

    glFlush()

def init():
    glClearColor(0.0, 0.0, 0.0, 0.0)  # Black background
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)

def main():
    glutInit()
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutInitWindowSize(600, 600)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Circle in OpenGL (Python)")
    init()
    glutDisplayFunc(display)
    glutMainLoop()

if __name__ == "__main__":
    main()
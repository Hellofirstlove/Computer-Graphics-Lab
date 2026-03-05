from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

def display():
    glClear(GL_COLOR_BUFFER_BIT)

    # -------- Trapezoid --------
    glColor3f(1.0, 1.0, 1.0)  # White
    glBegin(GL_POLYGON)
    glVertex3f(0.05, 0.05, 0.0)
    glVertex3f(0.35, 0.05, 0.0)
    glVertex3f(0.30, 0.35, 0.0)
    glVertex3f(0.10, 0.35, 0.0)
    glEnd()

    # -------- Rectangle --------
    glColor3f(0.0, 1.0, 0.0)  # Green
    glBegin(GL_QUADS)
    glVertex3f(0.5, 0.05, 0.0)
    glVertex3f(0.8, 0.05, 0.0)
    glVertex3f(0.8, 0.35, 0.0)
    glVertex3f(0.5, 0.35, 0.0)
    glEnd()

    # -------- Triangle --------
    glColor3f(0.0, 0.0, 1.0)  # Blue
    glBegin(GL_TRIANGLES)
    glVertex2f(0.30, 0.60) 
    glVertex2f(0.60, 0.60)
    glVertex2f(0.45, 0.85)
    glEnd()

    glFlush()


def init():
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)


def main():
    glutInit()
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutInitWindowSize(600, 600)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Demo in Python")
    init()
    glutDisplayFunc(display)
    glutMainLoop()


if __name__ == "__main__":
    main()
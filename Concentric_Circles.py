from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math


def draw_circle(center_x, center_y, radius, red, green, blue):
    glColor3f(red, green, blue)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(center_x, center_y)  # center

    for angle in range(0, 361):
        radian = math.radians(angle)
        x = center_x + radius * math.cos(radian)
        y = center_y + radius * math.sin(radian)
        glVertex2f(x, y)

    glEnd()


def display():
    glClear(GL_COLOR_BUFFER_BIT)

    center_x = 0.5
    center_y = 0.5

    # Draw concentric circles (outer → inner)
    draw_circle(center_x, center_y, 0.4, 1.0, 0.0, 0.0)  # Red
    draw_circle(center_x, center_y, 0.3, 0.0, 1.0, 0.0)  # Green
    draw_circle(center_x, center_y, 0.2, 0.0, 0.0, 1.0)  # Blue
    draw_circle(center_x, center_y, 0.1, 1.0, 1.0, 0.0)  # Yellow

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
    glutCreateWindow(b"Concentric Circles")
    init()
    glutDisplayFunc(display)
    glutMainLoop()


if __name__ == "__main__":
    main()
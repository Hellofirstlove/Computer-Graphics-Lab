from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

def drawPixel(x, y):
    glBegin(GL_POINTS)
    glVertex2i(x, y)
    glEnd()


def plotCirclePoints(xc, yc, x, y):

    drawPixel(xc + x, yc + y)
    drawPixel(xc - x, yc + y)
    drawPixel(xc + x, yc - y)
    drawPixel(xc - x, yc - y)

    drawPixel(xc + y, yc + x)
    drawPixel(xc - y, yc + x)
    drawPixel(xc + y, yc - x)
    drawPixel(xc - y, yc - x)

def midpointCircle(xc, yc, r):

    x = 0
    y = r

    d = 1 - r

    plotCirclePoints(xc, yc, x, y)

    while x < y:

        if d < 0:
            d = d + 2*x + 3

        else:
            d = d + 2*(x - y) + 5
            y -= 1

        x += 1

        plotCirclePoints(xc, yc, x, y)



def drawOlympicLogo():

    radius = 60

    
    glColor3f(0, 1, 1)
    midpointCircle(-140, 50, radius)
    
    glColor3f(0, 0, 0)
    midpointCircle(0, 50, radius)

    glColor3f(1, 0, 0)
    midpointCircle(140, 50, radius)

    glColor3f(1, 1, 0)
    midpointCircle(-70, -20, radius)

    glColor3f(0, 1, 0)
    midpointCircle(70, -20, radius)



def display():

    glClear(GL_COLOR_BUFFER_BIT)

    drawOlympicLogo()

    glFlush()


def init():

    glClearColor(1, 1, 1, 1)  # White Background

    gluOrtho2D(-300, 300, -300, 300)


glutInit()
glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
glutInitWindowSize(800, 600)
glutCreateWindow(b"Olympic Logo Using Midpoint Circle Algorithm")

init()

glPointSize(3)

glutDisplayFunc(display)

glutMainLoop()
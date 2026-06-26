from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time

# Global variables for animation
animation_time = 0.0

def draw_water_waves():
    """Draw animated waves in the river"""
    global animation_time
    
    glColor3f(0.0, 0.5, 1.0)  # Blue color for water
    
    wave_amplitude = 0.05
    wave_frequency = 3.0
    wave_speed = 2.0
    
    glBegin(GL_TRIANGLE_STRIP)
    
    # Draw multiple wave segments
    for i in range(0, 101):
        x = i / 100.0
        
        # First row of vertices (bottom of wave)
        y_bottom = 0.2
        glVertex3f(x, y_bottom, 0.0)
        
        # Second row of vertices (top of wave with sine wave)
        y_top = 0.5 + wave_amplitude * math.sin(wave_frequency * x * 2 * math.pi + animation_time * wave_speed)
        glVertex3f(x, y_top, 0.0)
    
    glEnd()


def draw_river_base():
    """Draw the base of the river"""
    glColor3f(0.2, 0.4, 0.8)  # Darker blue for river depth
    
    glBegin(GL_QUADS)
    glVertex3f(0.0, 0.2, 0.0)
    glVertex3f(1.0, 0.2, 0.0)
    glVertex3f(1.0, 0.5, 0.0)
    glVertex3f(0.0, 0.5, 0.0)
    glEnd()


def draw_boat(boat_x):
    """Draw a boat at given x position"""
    
    # -------- Boat Hull (Brown) --------
    glColor3f(0.6, 0.3, 0.0)  # Brown
    
    glBegin(GL_QUADS)
    # Main body of boat
    glVertex3f(boat_x - 0.08, 0.35, 0.0)
    glVertex3f(boat_x + 0.08, 0.35, 0.0)
    glVertex3f(boat_x + 0.06, 0.48, 0.0)
    glVertex3f(boat_x - 0.06, 0.48, 0.0)
    glEnd()
    
    # -------- Boat Top (Darker Brown) --------
    glColor3f(0.5, 0.25, 0.0)
    
    glBegin(GL_TRIANGLES)
    glVertex3f(boat_x - 0.06, 0.48, 0.0)
    glVertex3f(boat_x + 0.06, 0.48, 0.0)
    glVertex3f(boat_x, 0.55, 0.0)
    glEnd()
    
    # -------- Boat Sail (White) --------
    glColor3f(1.0, 1.0, 1.0)  # White
    
    glBegin(GL_TRIANGLES)
    glVertex3f(boat_x - 0.01, 0.48, 0.0)
    glVertex3f(boat_x + 0.01, 0.48, 0.0)
    glVertex3f(boat_x, 0.70, 0.0)
    glEnd()
    
    # -------- Sail Mast (Black) --------
    glColor3f(0.0, 0.0, 0.0)
    
    glBegin(GL_LINES)
    glVertex3f(boat_x, 0.48, 0.0)
    glVertex3f(boat_x, 0.71, 0.0)
    glEnd()


def draw_ground():
    """Draw the ground/scenery background"""
    # Sky
    glColor3f(0.5, 0.8, 1.0)  # Light blue sky
    
    glBegin(GL_QUADS)
    glVertex3f(0.0, 0.5, 0.0)
    glVertex3f(1.0, 0.5, 0.0)
    glVertex3f(1.0, 1.0, 0.0)
    glVertex3f(0.0, 1.0, 0.0)
    glEnd()
    
    # Ground
    glColor3f(0.2, 0.6, 0.2)  # Green grass
    
    glBegin(GL_QUADS)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(1.0, 0.0, 0.0)
    glVertex3f(1.0, 0.2, 0.0)
    glVertex3f(0.0, 0.2, 0.0)
    glEnd()


def draw_sun():
    """Draw a sun in the sky"""
    glColor3f(1.0, 1.0, 0.0)  # Yellow
    
    sun_x = 0.85
    sun_y = 0.85
    sun_radius = 0.05
    
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(sun_x, sun_y, 0.0)
    
    for i in range(33):
        angle = 2.0 * math.pi * i / 32.0
        x = sun_x + sun_radius * math.cos(angle)
        y = sun_y + sun_radius * math.sin(angle)
        glVertex3f(x, y, 0.0)
    
    glEnd()


def draw_trees():
    """Draw simple trees on the ground"""
    
    # Tree 1 - Trunk
    glColor3f(0.5, 0.25, 0.0)  # Brown
    glBegin(GL_QUADS)
    glVertex3f(0.1, 0.15, 0.0)
    glVertex3f(0.12, 0.15, 0.0)
    glVertex3f(0.12, 0.25, 0.0)
    glVertex3f(0.1, 0.25, 0.0)
    glEnd()
    
    # Tree 1 - Foliage
    glColor3f(0.0, 0.6, 0.0)  # Green
    glBegin(GL_TRIANGLES)
    glVertex3f(0.11, 0.25, 0.0)
    glVertex3f(0.05, 0.15, 0.0)
    glVertex3f(0.17, 0.15, 0.0)
    glEnd()
    
    # Tree 2 - Trunk
    glColor3f(0.5, 0.25, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(0.85, 0.15, 0.0)
    glVertex3f(0.87, 0.15, 0.0)
    glVertex3f(0.87, 0.25, 0.0)
    glVertex3f(0.85, 0.25, 0.0)
    glEnd()
    
    # Tree 2 - Foliage
    glColor3f(0.0, 0.6, 0.0)
    glBegin(GL_TRIANGLES)
    glVertex3f(0.86, 0.25, 0.0)
    glVertex3f(0.80, 0.15, 0.0)
    glVertex3f(0.92, 0.15, 0.0)
    glEnd()


def display():
    glClear(GL_COLOR_BUFFER_BIT)
    
    # Draw background elements
    draw_ground()
    draw_sun()
    draw_trees()
    
    # Draw river and water
    draw_river_base()
    draw_water_waves()
    
    # Draw boat (oscillates across the river)
    boat_x = 0.5 + 0.3 * math.sin(animation_time * 0.5)
    draw_boat(boat_x)
    
    glFlush()


def reshape(width, height):
    """Handle window reshape"""
    glViewport(0, 0, width, height)


def timer(value):
    """Timer function for animation"""
    global animation_time
    animation_time += 0.05
    
    glutPostRedisplay()
    glutTimerFunc(16, timer, 0)  # 16ms ≈ 60 FPS


def init():
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
    glMatrixMode(GL_MODELVIEW)


def main():
    glutInit()
    glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
    glutInitWindowSize(800, 600)
    glutInitWindowPosition(100, 100)
    glutCreateWindow(b"Boat in River with Animated Waves")
    
    init()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutTimerFunc(16, timer, 0)
    
    print("=" * 50)
    print("Boat in River with Animated Waves")
    print("=" * 50)
    print("\nFeatures:")
    print("- Animated waves using sine functions")
    print("- Boat moving back and forth on the river")
    print("- Scenic background with trees and sun")
    print("- Press ESC or close window to exit")
    print("\n" + "=" * 50)
    
    glutMainLoop()


if __name__ == "__main__":
    main()

#!/usr/bin/env python

from OpenGL.GL import *
from OpenGL.GLU import *
import pygame
from pygame.locals import *
import serial
import math
import time

# ---------------- Serial Setup ----------------
ser = serial.Serial('COM9', 115200, timeout=0.05)  # Change COM port if needed

# ---------------- Orientation State ----------------
alpha = 0.98       # Complementary filter coefficient
last_time = time.time()
roll = 0.0
pitch = 0.0
yaw = 0.0

# ---------------- Display variables ----------------
yaw_mode = False  # Toggle yaw rotation
ax = ay = az = 0.0  # Raw values for display

# ---------------- OpenGL & Pygame Setup ----------------
def resize(width, height):
    if height == 0:
        height = 1
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width / float(height), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def init():
    glShadeModel(GL_SMOOTH)
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClearDepth(1.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

def drawText(position, textString):
    font = pygame.font.SysFont("Courier", 18, True)
    textSurface = font.render(textString, True, (255,255,255,255), (0,0,0,255))
    textData = pygame.image.tostring(textSurface, "RGBA", True)
    glRasterPos3d(*position)
    glDrawPixels(textSurface.get_width(), textSurface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, textData)

# ---------------- Complementary Filter ----------------
def update_orientation(ax, ay, az, gx, gy, gz):
    """
    ax, ay, az: accelerometer in m/s²
    gx, gy, gz: gyroscope in rad/s
    """
    global roll, pitch, yaw, last_time

    now = time.time()
    dt = now - last_time
    last_time = now

    if dt <= 0 or dt > 0.1:  # ignore large dt spikes
        return roll, pitch, yaw

    # --- Accelerometer angles (gravity projection) ---
    accel_roll  = math.degrees(math.atan2(-ay, az))
    accel_pitch = math.degrees(math.atan2(ax, math.sqrt(ay*ay + az*az)))

    # --- Gyro integration (rad/s → deg/s) ---
    roll_gyro  = roll + math.degrees(gx * dt)
    pitch_gyro = pitch + math.degrees(gy * dt)
    yaw_gyro   = yaw + math.degrees(gz * dt)

    # --- Complementary filter ---
    roll  = alpha * roll_gyro  + (1 - alpha) * accel_roll
    pitch = alpha * pitch_gyro + (1 - alpha) * accel_pitch
    yaw   = yaw_gyro  # yaw is only gyro

    return roll, pitch, yaw

# ---------------- Cube Drawing ----------------
def draw_cube():
    global roll, pitch, yaw

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -7.0)

    # Display angles
    osd_text = f"Pitch: {pitch:.2f}, Roll: {roll:.2f}"
    if yaw_mode:
        osd_text += f", Yaw: {yaw:.2f}"
    drawText((-2, -2, 2), osd_text)

    # Apply rotation to cube
    if yaw_mode:
        glRotatef(yaw, 0.0, 1.0, 0.0)  # Yaw
    glRotatef(roll, 1.0, 0.0, 0.0)     # Roll
    glRotatef(pitch, 0.0, 0.0, 1.0)    # Pitch

    # Draw cube faces
    glBegin(GL_QUADS)
    # Top
    glColor3f(0.0,1.0,0.0)
    glVertex3f( 1.0, 0.2,-1.0)
    glVertex3f(-1.0, 0.2,-1.0)
    glVertex3f(-1.0, 0.2, 1.0)
    glVertex3f( 1.0, 0.2, 1.0)
    # Bottom
    glColor3f(1.0,0.5,0.0)
    glVertex3f( 1.0,-0.2, 1.0)
    glVertex3f(-1.0,-0.2, 1.0)
    glVertex3f(-1.0,-0.2,-1.0)
    glVertex3f( 1.0,-0.2,-1.0)
    # Front
    glColor3f(1.0,0.0,0.0)
    glVertex3f( 1.0, 0.2, 1.0)
    glVertex3f(-1.0, 0.2, 1.0)
    glVertex3f(-1.0,-0.2, 1.0)
    glVertex3f( 1.0,-0.2, 1.0)
    # Back
    glColor3f(1.0,1.0,0.0)
    glVertex3f( 1.0,-0.2,-1.0)
    glVertex3f(-1.0,-0.2,-1.0)
    glVertex3f(-1.0, 0.2,-1.0)
    glVertex3f( 1.0, 0.2,-1.0)
    # Left
    glColor3f(0.0,0.0,1.0)
    glVertex3f(-1.0, 0.2, 1.0)
    glVertex3f(-1.0, 0.2,-1.0)
    glVertex3f(-1.0,-0.2,-1.0)
    glVertex3f(-1.0,-0.2, 1.0)
    # Right
    glColor3f(1.0,0.0,1.0)
    glVertex3f( 1.0, 0.2,-1.0)
    glVertex3f( 1.0, 0.2, 1.0)
    glVertex3f( 1.0,-0.2, 1.0)
    glVertex3f( 1.0,-0.2,-1.0)
    glEnd()

# ---------------- Read Serial ----------------
def read_serial():
    global ax, ay, az, roll, pitch, yaw
    try:
        line = ser.readline().decode().strip()
        if line.count(",") == 5:
            ax_raw, ay_raw, az_raw, gx_raw, gy_raw, gz_raw = map(float, line.split(","))
            roll, pitch, yaw = update_orientation(ax_raw, ay_raw, az_raw, gx_raw, gy_raw, gz_raw)
    except:
        pass

# ---------------- Main Loop ----------------
def main():
    global yaw_mode
    pygame.init()
    video_flags = OPENGL | DOUBLEBUF
    screen = pygame.display.set_mode((640,480), video_flags)
    pygame.display.set_caption("ICM20948 Cube Viewer (Esc to quit, Z toggles yaw)")
    resize(640,480)
    init()

    while True:
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                ser.close()
                pygame.quit()
                return
            if event.type == KEYDOWN and event.key == K_z:
                yaw_mode = not yaw_mode

        read_serial()
        draw_cube()
        pygame.display.flip()


if __name__ == '__main__':
    main()

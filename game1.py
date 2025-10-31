import serial
import serial.tools.list_ports
import time
import re
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math

# ==============================
# SERIAL CONFIGURATION
# ==============================
BAUD = 38400

# ==============================
# FIND ACTIVE SERIAL PORT
# ==============================
def find_active_port():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    print("Available ports:", ports)

    for port in ports:
        try:
            ser = serial.Serial(port, BAUD, timeout=1)
            print(f"Testing {port}...")
            time.sleep(2)
            data = ser.readline().decode(errors="ignore").strip()
            if data:
                print(f"✅ Active data found on {port}: {data}")
                return ser
            ser.close()
        except Exception:
            pass

    print("❌ No active COM port produced data.")
    return None

# ==============================
# PARSE SENSOR DATA (X, Y)
# ==============================
def parse_xy(line):
    """
    Example line: 08:59:30.001 -> X: 448 | Y: 460
    """
    match = re.search(r"X:\s*(-?\d+)\s*\|\s*Y:\s*(-?\d+)", line)
    if match:
        x = int(match.group(1))
        y = int(match.group(2))
        return x, y
    return None, None

# ==============================
# DRAW SIMPLE 3D AIRPLANE
# ==============================
def draw_airplane():
    glBegin(GL_TRIANGLES)
    # Nose
    glColor3f(0.2, 0.8, 1.0)
    glVertex3f(0.0, 0.2, 0.8)
    glVertex3f(-0.2, -0.2, 0.0)
    glVertex3f(0.2, -0.2, 0.0)

    # Left wing
    glColor3f(0.0, 0.6, 1.0)
    glVertex3f(-0.2, -0.1, 0.0)
    glVertex3f(-0.8, 0.0, -0.4)
    glVertex3f(-0.2, 0.0, 0.0)

    # Right wing
    glColor3f(0.0, 0.6, 1.0)
    glVertex3f(0.2, -0.1, 0.0)
    glVertex3f(0.8, 0.0, -0.4)
    glVertex3f(0.2, 0.0, 0.0)

    # Tail
    glColor3f(0.0, 0.4, 0.9)
    glVertex3f(-0.1, 0.0, -0.5)
    glVertex3f(0.1, 0.0, -0.5)
    glVertex3f(0.0, 0.2, -0.6)
    glEnd()

# ==============================
# MAIN OPENGL LOOP
# ==============================
def start_3d_view(serial_port):
    pygame.init()
    display = (1000, 700)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Airplane Motion (X/Y from Serial)")

    glEnable(GL_DEPTH_TEST)
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)

    # Move camera back
    glTranslatef(0.0, 0.0, -5)

    # Airplane rotation angles
    pitch = 0
    roll = 0

    print("🎮 3D simulation started — move sensor to control rotation.")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        # Read new data from serial
        try:
            if serial_port.in_waiting:
                line = serial_port.readline().decode(errors="ignore").strip()
                x, y = parse_xy(line)
                if x is not None and y is not None:
                    # Convert X/Y into pitch and roll angles
                    roll = (x - 450) * 0.3   # rotation around Z-axis
                    pitch = (y - 450) * 0.3  # rotation around X-axis
                    print(f"X={x}, Y={y} => Pitch={pitch:.2f}, Roll={roll:.2f}")
        except Exception as e:
            print("Serial read error:", e)

        # === RENDER ===
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Reset modelview each frame
        glLoadIdentity()

        # Camera view
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        # Apply rotations
        glRotatef(pitch, 1, 0, 0)  # Pitch (nose up/down)
        glRotatef(roll, 0, 0, 1)   # Roll (tilt wings)

        draw_airplane()
        pygame.display.flip()
        pygame.time.wait(16)  # ~60 FPS

    serial_port.close()
    pygame.quit()
    print("🔚 Simulation ended.")

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    ser = find_active_port()
    if ser:
        start_3d_view(ser)

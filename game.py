import serial
import serial.tools.list_ports
import time
import pygame
import re
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Serial configuration
BAUD = 38400

def find_working_port():
    """Scan for active COM port with expected data format in descending order"""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No COM ports found!")
        return None, None

    # Sort ports by COM number (highest first)
    def get_com_num(port):
        try:
            return int(''.join(filter(str.isdigit, port.device)))
        except:
            return 0
    ports.sort(key=get_com_num, reverse=True)

    # Print available ports in descending order
    print("\n🔍 Available COM ports (highest to lowest):")
    for port in ports:
        print(f"  • {port.device}: {port.description}")

    # Try preferred ports first (Bluetooth / HC-05 / Arduino)
    preferred_keywords = ("HC-05", "Bluetooth", "Arduino", "Serial")
    def port_priority(p):
        desc = (p.description or "").lower()
        for kw in preferred_keywords:
            if kw.lower() in desc:
                return 0
        return 1
    ports.sort(key=port_priority)  # Prioritize but keep descending order within priority

    # Detection strategy: try each port, require multiple valid readings
    for port in ports:
        print(f"\n📡 Testing {port.device} ({port.description})...")
        ser = None
        try:
            ser = serial.Serial(port.device, BAUD, timeout=0.1)
            time.sleep(0.1)  # Brief pause for device
            ser.reset_input_buffer()

            valid_count = 0
            attempts = 0
            start = time.time()
            
            # Try for up to 2 seconds
            while time.time() - start < 2.0 and attempts < 60:
                attempts += 1
                try:
                    raw = ser.readline()
                    if not raw:
                        time.sleep(0.02)
                        continue
                    
                    data = raw.decode(errors='ignore')
                    print(f"  raw[{port.device}]: {repr(data)}")
                    s = data.strip()
                    
                    if s and "X:" in s and "Y:" in s:
                        print(f"    attempting parse: {s}")
                        x_norm, y_norm = parse_sensor_data(s)
                        if x_norm is not None:  # Successfully parsed
                            valid_count += 1
                            if valid_count >= 2:  # Require 2 valid readings
                                print(f"✅ Found joystick on {port.device}")
                                print(f"   Last reading: x_norm={x_norm:.3f}, y_norm={y_norm:.3f}")
                                return ser, port.device
                
                except Exception as e:
                    print(f"    parse error: {e}")
                    time.sleep(0.02)
                    continue

            if ser:
                ser.close()

        except Exception as e:
            print(f"Error on {port.device}: {e}")
            if ser:
                try:
                    ser.close()
                except:
                    pass
            continue

    print("\n❌ No joystick found!")
    return None, None

def parse_sensor_data(line):
    """Parse data in format: X:448,Y:461"""
    try:
        # Split by comma and extract numbers
        parts = line.split(',')
        if len(parts) >= 2:
            x_str = parts[0]
            y_str = parts[1]
            
            # Extract numbers only
            x = int(''.join(c for c in x_str if c.isdigit()))
            y = int(''.join(c for c in y_str if c.isdigit()))
            
            # Normalize to -1..1 range
            x_norm = (x - 512) / 512.0
            y_norm = (y - 512) / 512.0
            
            return x_norm, y_norm
    except (ValueError, AttributeError, IndexError) as e:
        pass
    return None, None

def draw_cube():
    """Draw a cube using immediate mode (no freeglut required)"""
    vertices = [
        [1, 1, -1], [1, -1, -1], [-1, -1, -1], [-1, 1, -1],
        [1, 1, 1], [1, -1, 1], [-1, -1, 1], [-1, 1, 1]
    ]
    
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
    ]
    
    glBegin(GL_LINES)
    glColor3f(1, 1, 1)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

def draw_airplane(x, y, z):
    """Draw a simple airplane using basic OpenGL primitives"""
    glPushMatrix()
    glTranslatef(x, y, z)
    
    # Fuselage (main body)
    glColor3f(0.8, 0.8, 0.8)
    glPushMatrix()
    glScalef(1.0, 0.3, 0.3)
    draw_cube()
    glPopMatrix()
    
    # Wings
    glColor3f(0.2, 0.2, 0.8)
    glBegin(GL_QUADS)
    # Right wing
    glVertex3f(0.3, 0, 0.8)
    glVertex3f(-0.3, 0, 0.8)
    glVertex3f(-0.8, 0, 0.2)
    glVertex3f(0.8, 0, 0.2)
    # Left wing
    glVertex3f(0.3, 0, -0.8)
    glVertex3f(-0.3, 0, -0.8)
    glVertex3f(-0.8, 0, -0.2)
    glVertex3f(0.8, 0, -0.2)
    glEnd()
    
    # Tail
    glColor3f(0.8, 0.2, 0.2)
    glBegin(GL_TRIANGLES)
    # Vertical stabilizer
    glVertex3f(-0.8, 0, 0)
    glVertex3f(-1.2, 0.5, 0)
    glVertex3f(-0.8, 0, 0)
    # Horizontal stabilizer
    glVertex3f(-0.8, -0.1, 0.3)
    glVertex3f(-1.2, -0.1, 0)
    glVertex3f(-0.8, -0.1, -0.3)
    glEnd()
    
    glPopMatrix()

def main():
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("3D Airplane Controller - No freeglut")
    
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -10)
    glRotatef(-30, 1, 0, 0)
    
    glEnable(GL_DEPTH_TEST)
    
    # Find working serial port
    ser, port = find_working_port()
    if not ser:
        print("Failed to find working serial port. Exiting.")
        return
    
    print(f"Connected to {port}. Starting 3D visualization...")
    
    airplane_x = 0
    airplane_y = 0
    airplane_z = 0
    move_speed = 0.1
    
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Read serial data
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode(errors='ignore').strip()
                    if line:
                        print(f"Raw data: {line}")
                        
                        x_norm, y_norm = parse_sensor_data(line)
                        if x_norm is not None and y_norm is not None:
                            airplane_x += x_norm * move_speed
                            airplane_y += y_norm * move_speed
                            airplane_z -= 0.05
                            
                            if abs(airplane_x) > 8 or abs(airplane_y) > 8:
                                airplane_x = 0
                                airplane_y = 0
                                airplane_z = 0
                            
                            print(f"Position - X: {airplane_x:.2f}, Y: {airplane_y:.2f}, Z: {airplane_z:.2f}")
                
                except Exception as e:
                    print(f"Error reading serial data: {e}")
            
            # Clear and draw
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Draw coordinate system
            glBegin(GL_LINES)
            glColor3f(1, 0, 0)  # X - Red
            glVertex3f(-5, 0, 0); glVertex3f(5, 0, 0)
            glColor3f(0, 1, 0)  # Y - Green
            glVertex3f(0, -5, 0); glVertex3f(0, 5, 0)
            glColor3f(0, 0, 1)  # Z - Blue
            glVertex3f(0, 0, -5); glVertex3f(0, 0, 5)
            glEnd()
            
            draw_airplane(airplane_x, airplane_y, airplane_z)
            
            pygame.display.flip()
            clock.tick(60)
    
    except KeyboardInterrupt:
        print("Program interrupted by user")
    
    finally:
        if ser and ser.is_open:
            ser.close()
        pygame.quit()

if __name__ == "__main__":
    main()
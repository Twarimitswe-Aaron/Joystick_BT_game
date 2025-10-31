import serial
import serial.tools.list_ports
import time
import pygame
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from collections import deque

# Serial configuration
BAUD = 38400

def find_working_port():
    """Scan for active COM port with expected data format in descending order"""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No COM ports found!")
        return None, None

    def get_com_num(port):
        try:
            return int(''.join(filter(str.isdigit, port.device)))
        except:
            return 0
    ports.sort(key=get_com_num, reverse=True)

    print("\n🔍 Available COM ports (highest to lowest):")
    for port in ports:
        print(f"  • {port.device}: {port.description}")

    preferred_keywords = ("HC-05", "Bluetooth", "Arduino", "Serial")
    def port_priority(p):
        desc = (p.description or "").lower()
        for kw in preferred_keywords:
            if kw.lower() in desc:
                return 0
        return 1
    ports.sort(key=port_priority)

    for port in ports:
        print(f"\n📡 Testing {port.device} ({port.description})...")
        ser = None
        try:
            ser = serial.Serial(port.device, BAUD, timeout=0.1)
            time.sleep(0.1)
            ser.reset_input_buffer()

            valid_count = 0
            attempts = 0
            start = time.time()
            
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
                        if x_norm is not None:
                            valid_count += 1
                            if valid_count >= 2:
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
        parts = line.split(',')
        if len(parts) >= 2:
            x_str = parts[0]
            y_str = parts[1]
            
            x = int(''.join(c for c in x_str if c.isdigit()))
            y = int(''.join(c for c in y_str if c.isdigit()))
            
            x_norm = (x - 512) / 512.0
            y_norm = (y - 512) / 512.0
            
            return x_norm, y_norm
    except (ValueError, AttributeError, IndexError):
        pass
    return None, None

def draw_grid(size=10, spacing=1):
    """Draw a ground grid"""
    glColor4f(0.3, 0.3, 0.3, 0.5)
    glBegin(GL_LINES)
    for i in range(-size, size + 1):
        glVertex3f(i * spacing, -3, -size * spacing)
        glVertex3f(i * spacing, -3, size * spacing)
        glVertex3f(-size * spacing, -3, i * spacing)
        glVertex3f(size * spacing, -3, i * spacing)
    glEnd()

def draw_airplane(x, y, z, pitch=0, roll=0):
    """Draw enhanced airplane with rotation"""
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(roll * 20, 0, 0, 1)  # Roll rotation
    glRotatef(pitch * 10, 1, 0, 0)  # Pitch rotation
    
    # Fuselage with gradient effect
    glBegin(GL_QUADS)
    # Top
    glColor3f(0.9, 0.9, 0.9)
    glVertex3f(1.0, 0.15, 0.15)
    glVertex3f(-1.0, 0.15, 0.15)
    glColor3f(0.7, 0.7, 0.7)
    glVertex3f(-1.0, 0.15, -0.15)
    glVertex3f(1.0, 0.15, -0.15)
    
    # Bottom
    glColor3f(0.6, 0.6, 0.6)
    glVertex3f(1.0, -0.15, 0.15)
    glVertex3f(-1.0, -0.15, 0.15)
    glVertex3f(-1.0, -0.15, -0.15)
    glVertex3f(1.0, -0.15, -0.15)
    
    # Sides
    glColor3f(0.8, 0.8, 0.8)
    glVertex3f(1.0, 0.15, 0.15)
    glVertex3f(1.0, -0.15, 0.15)
    glVertex3f(-1.0, -0.15, 0.15)
    glVertex3f(-1.0, 0.15, 0.15)
    
    glVertex3f(1.0, 0.15, -0.15)
    glVertex3f(1.0, -0.15, -0.15)
    glVertex3f(-1.0, -0.15, -0.15)
    glVertex3f(-1.0, 0.15, -0.15)
    glEnd()
    
    # Wings with gradient
    glBegin(GL_QUADS)
    # Right wing
    glColor3f(0.2, 0.4, 0.9)
    glVertex3f(0.3, 0.05, 1.2)
    glVertex3f(-0.3, 0.05, 1.2)
    glColor3f(0.1, 0.2, 0.6)
    glVertex3f(-0.8, 0.05, 0.2)
    glVertex3f(0.8, 0.05, 0.2)
    
    # Left wing
    glColor3f(0.2, 0.4, 0.9)
    glVertex3f(0.3, 0.05, -1.2)
    glVertex3f(-0.3, 0.05, -1.2)
    glColor3f(0.1, 0.2, 0.6)
    glVertex3f(-0.8, 0.05, -0.2)
    glVertex3f(0.8, 0.05, -0.2)
    glEnd()
    
    # Tail fin
    glColor3f(0.9, 0.3, 0.3)
    glBegin(GL_TRIANGLES)
    glVertex3f(-0.8, 0, 0)
    glVertex3f(-1.3, 0.6, 0)
    glVertex3f(-1.3, 0, 0)
    glEnd()
    
    # Horizontal stabilizers
    glColor3f(0.8, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-0.8, 0, 0.5)
    glVertex3f(-1.3, 0, 0.3)
    glVertex3f(-1.3, 0, -0.3)
    glVertex3f(-0.8, 0, -0.5)
    glEnd()
    
    # Cockpit
    glColor3f(0.3, 0.6, 0.9)
    glBegin(GL_TRIANGLES)
    glVertex3f(0.8, 0.15, 0.1)
    glVertex3f(1.0, 0.25, 0)
    glVertex3f(0.8, 0.15, -0.1)
    glEnd()
    
    glPopMatrix()

def draw_flight_path(trail, current_pos):
    """Draw the flight path trail"""
    if len(trail) < 2:
        return
    
    glLineWidth(2.0)
    glBegin(GL_LINE_STRIP)
    for i, pos in enumerate(trail):
        # Fade older trail points
        alpha = i / len(trail)
        glColor4f(0.2, 0.8, 1.0, alpha * 0.7)
        glVertex3f(pos[0], pos[1], pos[2])
    glEnd()
    glLineWidth(1.0)

def draw_hud_line(x1, y1, x2, y2, color=(1, 1, 1)):
    """Draw a line in HUD overlay"""
    glColor3f(*color)
    glBegin(GL_LINES)
    glVertex2f(x1, y1)
    glVertex2f(x2, y2)
    glEnd()

def draw_crosshair():
    """Draw center crosshair"""
    glColor3f(0.2, 1.0, 0.2)
    glLineWidth(2.0)
    size = 0.02
    gap = 0.01
    
    # Horizontal
    glBegin(GL_LINES)
    glVertex2f(-size - gap, 0)
    glVertex2f(-gap, 0)
    glVertex2f(gap, 0)
    glVertex2f(size + gap, 0)
    
    # Vertical
    glVertex2f(0, -size - gap)
    glVertex2f(0, -gap)
    glVertex2f(0, gap)
    glVertex2f(0, size + gap)
    glEnd()
    
    # Center circle
    glBegin(GL_LINE_LOOP)
    for i in range(20):
        angle = 2 * math.pi * i / 20
        glVertex2f(gap * math.cos(angle), gap * math.sin(angle))
    glEnd()
    glLineWidth(1.0)

def draw_artificial_horizon(pitch, roll):
    """Draw artificial horizon indicator"""
    glPushMatrix()
    glTranslatef(-0.85, -0.7, 0)
    glRotatef(roll * 20, 0, 0, 1)
    
    # Sky
    glColor4f(0.2, 0.4, 0.8, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(-0.1, 0)
    glVertex2f(0.1, 0)
    glVertex2f(0.1, 0.15)
    glVertex2f(-0.1, 0.15)
    glEnd()
    
    # Ground
    glColor4f(0.4, 0.3, 0.2, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(-0.1, 0)
    glVertex2f(0.1, 0)
    glVertex2f(0.1, -0.15)
    glVertex2f(-0.1, -0.15)
    glEnd()
    
    # Horizon line
    glColor3f(1, 1, 1)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glVertex2f(-0.1, 0)
    glVertex2f(0.1, 0)
    glEnd()
    glLineWidth(1.0)
    
    glPopMatrix()
    
    # Frame
    glColor3f(0.5, 0.5, 0.5)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex2f(-0.95, -0.85)
    glVertex2f(-0.75, -0.85)
    glVertex2f(-0.75, -0.55)
    glVertex2f(-0.95, -0.55)
    glEnd()
    glLineWidth(1.0)

def render_text_pygame(text, x, y, font, color=(255, 255, 255)):
    """Render text using pygame"""
    text_surface = font.render(text, True, color)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    
    glWindowPos2d(x, y)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                 GL_RGBA, GL_UNSIGNED_BYTE, text_data)

def main():
    # Initialize pygame with performance optimizations
    pygame.init()
    display = (1200, 800)
    
    # Enable hardware acceleration and double buffering
    pygame.display.gl_set_attribute(pygame.GL_SWAP_CONTROL, 1)  # Enable VSync if available
    screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL | HWSURFACE)
    pygame.display.set_caption("Advanced Flight Control System (Optimized)")
    
    # Set up OpenGL for better performance
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glShadeModel(GL_SMOOTH)
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
    
    # Set up display lists for static elements
    grid_dl = glGenLists(1)
    glNewList(grid_dl, GL_COMPILE)
    draw_grid(15, 1)
    glEndList()
    
    # Pre-compile axes display list
    axes_dl = glGenLists(1)
    glNewList(axes_dl, GL_COMPILE)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glColor3f(1, 0.3, 0.3); glVertex3f(-10, 0, 0); glVertex3f(10, 0, 0)  # X axis (red)
    glColor3f(0.3, 1, 0.3); glVertex3f(0, -10, 0); glVertex3f(0, 10, 0)  # Y axis (green)
    glColor3f(0.3, 0.3, 1); glVertex3f(0, 0, -10); glVertex3f(0, 0, 10)  # Z axis (blue)
    glEnd()
    glLineWidth(1.0)
    glEndList()
    
    # Cache for text surfaces
    text_cache = {}
    
    # Fonts - load once and reuse
    font_large = pygame.font.SysFont('Arial', 48, bold=True)
    font_medium = pygame.font.SysFont('Arial', 32, bold=True)
    font_small = pygame.font.SysFont('Arial', 24)
    
    # Set up the projection matrix once
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, (display[0] / display[1]), 0.1, 100.0)
    
    # Set up the modelview matrix
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -15)
    glRotatef(-25, 1, 0, 0)
    
    ser, port = find_working_port()
    if not ser:
        print("Failed to find working serial port. Exiting.")
        return
    
    print(f"Connected to {port}. Starting flight simulation...")
    
    # Flight state
    airplane_x = 0
    airplane_y = 0
    airplane_z = 0
    velocity = 0
    pitch = 0
    roll = 0
    move_speed = 0.12
    
    # Trail for flight path
    trail = deque(maxlen=100)
    
    # Stats
    distance_traveled = 0
    flight_time = 0
    start_time = time.time()
    
    # Performance tracking
    clock = pygame.time.Clock()
    running = True
    frame_count = 0
    last_fps_update = time.time()
    fps = 0
    
    # Target FPS
    TARGET_FPS = 60
    
    # Frame time smoothing
    frame_times = deque(maxlen=60)
    avg_frame_time = 0.016  # Start with 60 FPS
    
    try:
        while running:
            frame_start = time.time()
            dt = min(clock.tick(TARGET_FPS) / 1000.0, 0.1)  # Cap dt to prevent physics issues
            flight_time = time.time() - start_time
            
            # Calculate FPS
            frame_count += 1
            if frame_start - last_fps_update >= 1.0:  # Update FPS counter every second
                fps = frame_count / (frame_start - last_fps_update)
                frame_count = 0
                last_fps_update = frame_start
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        # Reset position
                        airplane_x = airplane_y = airplane_z = 0
                        trail.clear()
                        distance_traveled = 0
            
            # Read serial data
            x_input, y_input = 0, 0
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode(errors='ignore').strip()
                    if line:
                        x_norm, y_norm = parse_sensor_data(line)
                        if x_norm is not None and y_norm is not None:
                            x_input = x_norm
                            y_input = y_norm
                            
                            # Update position
                            old_x, old_y, old_z = airplane_x, airplane_y, airplane_z
                            airplane_x += x_norm * move_speed
                            airplane_y += y_norm * move_speed
                            airplane_z -= 0.03
                            
                            # Calculate distance
                            dx = airplane_x - old_x
                            dy = airplane_y - old_y
                            dz = airplane_z - old_z
                            distance_traveled += math.sqrt(dx*dx + dy*dy + dz*dz)
                            
                            # Update rotation
                            roll = x_norm
                            pitch = y_norm
                            velocity = math.sqrt(dx*dx + dy*dy + dz*dz) * 60
                            
                            # Reset if out of bounds
                            if abs(airplane_x) > 10 or abs(airplane_y) > 10 or airplane_z < -15:
                                airplane_x = airplane_y = airplane_z = 0
                                trail.clear()
                            
                            trail.append((airplane_x, airplane_y, airplane_z))
                
                except Exception as e:
                    print(f"Error reading serial data: {e}")
            
            # 3D rendering - clear buffers
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Draw pre-compiled display lists for static elements
            glCallList(grid_dl)  # Draw grid from display list
            glCallList(axes_dl)   # Draw axes from display list
            
            # Draw flight path with optimized rendering
            if len(trail) > 1:
                glEnable(GL_LINE_SMOOTH)
                glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
                glLineWidth(1.5)
                glBegin(GL_LINE_STRIP)
                glColor4f(0.8, 1.0, 0.8, 0.7)  # Semi-transparent light green
                for point in trail:
                    glVertex3f(*point)
                glEnd()
                glLineWidth(1.0)
            
            # Draw airplane with optimized rendering
            glPushMatrix()
            glTranslatef(airplane_x, airplane_y, airplane_z)
            glRotatef(roll * 30, 0, 0, 1)  # Roll
            glRotatef(pitch * 30, 1, 0, 0)  # Pitch
            
            # Simple airplane shape (optimized)
            glBegin(GL_TRIANGLES)
            # Fuselage
            glColor3f(0.8, 0.8, 0.8)
            glVertex3f(0, 0.1, 0.3)
            glVertex3f(-0.1, -0.1, -0.1)
            glVertex3f(0.1, -0.1, -0.1)
            
            # Wings
            glColor3f(0.6, 0.6, 0.8)
            glVertex3f(0.8, 0, 0)
            glVertex3f(-0.8, 0, 0)
            glVertex3f(0, 0, -0.1)
            
            # Tail
            glColor3f(0.7, 0.7, 0.7)
            glVertex3f(0, 0.05, 0.2)
            glVertex3f(0, -0.05, 0.2)
            glVertex3f(0, 0, 0.4)
            glEnd()
            glPopMatrix()
            
            # HUD Overlay
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(-1, 1, -1, 1, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            
            # Draw crosshair
            draw_crosshair()
            
            # Draw artificial horizon
            draw_artificial_horizon(pitch, roll)
            
            # HUD frame
            glColor3f(0.2, 0.8, 1.0)
            glLineWidth(1.5)
            glBegin(GL_LINE_STRIP)
            glVertex2f(-0.95, 0.95)
            glVertex2f(-0.7, 0.95)
            glEnd()
            glBegin(GL_LINE_STRIP)
            glVertex2f(0.95, 0.95)
            glVertex2f(0.7, 0.95)
            glEnd()
            glLineWidth(1.0)
            
            glEnable(GL_DEPTH_TEST)
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            
            # Text overlay with caching and batching
            def draw_cached_text(text, x, y, font, color):
                cache_key = f"{text}_{x}_{y}_{color}"
                if cache_key not in text_cache:
                    text_surface = font.render(text, True, color)
                    text_cache[cache_key] = (text_surface, (x, y))
                else:
                    text_surface, (x, y) = text_cache[cache_key]
                
                # Convert to OpenGL texture once and render
                text_data = pygame.image.tostring(text_surface, "RGBA", True)
                glWindowPos2d(x, y)
                glDrawPixels(text_surface.get_width(), text_surface.get_height(),
                            GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            
            # Only update text when values change
            draw_cached_text(f"ALT: {abs(airplane_z):.1f}m", 20, display[1] - 40, font_medium, (0, 255, 100))
            draw_cached_text(f"SPD: {velocity:.1f}m/s", 20, display[1] - 80, font_medium, (100, 200, 255))
            draw_cached_text(f"DST: {distance_traveled:.1f}m", 20, display[1] - 120, font_small, (255, 200, 100))
            draw_cached_text(f"FPS: {fps:.1f}", display[0] - 150, display[1] - 150, font_small, (200, 200, 200))
            
            # Time display (updates every second)
            time_text = f"TIME: {int(flight_time//60)}:{int(flight_time%60):02d}"
            draw_cached_text(time_text, 20, display[1] - 150, font_small, (255, 255, 255))
            
            # Position display
            draw_cached_text(f"X: {airplane_x:+.1f}", display[0] - 150, display[1] - 40, font_small, (255, 100, 100))
            draw_cached_text(f"Y: {airplane_y:+.1f}", display[0] - 150, display[1] - 70, font_small, (100, 255, 100))
            draw_cached_text(f"Z: {airplane_z:+.1f}", display[0] - 150, display[1] - 100, font_small, (100, 100, 255))
            
            # Controls hint (static, cache once)
            draw_cached_text("ESC: Quit | R: Reset", 20, 20, font_small, (150, 150, 150))
            
            # Limit FPS and update display
            pygame.display.flip()
            
            # Calculate frame time for next frame
            frame_time = time.time() - frame_start
            frame_times.append(frame_time)
            avg_frame_time = sum(frame_times) / len(frame_times)
            
            # Clear text cache if it gets too big
            if len(text_cache) > 100:
                text_cache.clear()
    
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    
    finally:
        if ser and ser.is_open:
            ser.close()
        pygame.quit()

if __name__ == "__main__":
    main()
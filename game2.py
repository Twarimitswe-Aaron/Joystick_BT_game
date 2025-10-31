import serial
import serial.tools.list_ports
import time
import pygame
import math
import sys
import random

BAUD = 38400  # for HC-05 Bluetooth

def find_bluetooth_port():
    # Get all ports and sort them by COM number in descending order
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No COM ports found!")
        sys.exit(1)

    # Sort ports by COM number (highest first)
    def get_com_num(port):
        try:
            return int(''.join(filter(str.isdigit, port.device)))
        except:
            return 0

    ports.sort(key=get_com_num, reverse=True)

    print("\n🔍 Available COM ports (highest to lowest):")
    for port in ports:
        print(f"  • {port.device}: {port.description}")

    # Try preferred ports first (Bluetooth / HC-05 / Arduino), then all ports
    preferred_keywords = ("HC-05", "Bluetooth", "Arduino", "Serial")
    def port_priority(p):
        desc = (p.description or "").lower()
        for kw in preferred_keywords:
            if kw.lower() in desc:
                return 0
        return 1

    ports.sort(key=port_priority)

    # Detection strategy: for each port, open and read bursts, require multiple valid lines
    for port in ports:
        print(f"\n📡 Testing {port.device} ({port.description})...")
        ser = None
        try:
            # Open with short timeout to not block; we will poll in small sleeps
            ser = serial.Serial(port.device, BAUD, timeout=0.1)
            # Give device a small moment to start sending
            time.sleep(0.1)
            ser.reset_input_buffer()

            valid_count = 0
            attempts = 0
            start = time.time()
            # Try up to 2 seconds, reading small bursts
            while time.time() - start < 2.0 and attempts < 60:
                attempts += 1
                try:
                    # Read one line (non-blocking due to timeout)
                    raw = ser.readline()
                    if not raw:
                        time.sleep(0.02)
                        continue
                    data = raw.decode(errors='ignore')
                    print(f"  raw[{port.device}]: {repr(data)}")
                    s = data.strip()
                    if not s:
                        continue

                    # Accept formats like 'X:448,Y:461' or 'X: 448 | Y: 461'
                    if "X:" in s and "Y:" in s:
                        # Normalize separators
                        if "|" in s:
                            parts = s.replace("|", ",").split(",")
                        else:
                            parts = s.split(",")

                        if len(parts) >= 2:
                            try:
                                x_part = parts[0]
                                y_part = parts[1]
                                x = int(''.join(c for c in x_part if c.isdigit()))
                                y = int(''.join(c for c in y_part if c.isdigit()))
                                print(f"    parsed X={x} Y={y}")
                                if 0 <= x <= 1023 and 0 <= y <= 1023:
                                    valid_count += 1
                                    # require 2 valid readings to be confident
                                    if valid_count >= 2:
                                        print(f"✅ Found joystick on {port.device}")
                                        print(f"   Last reading: X={x}, Y={y}")
                                        return ser
                            except Exception as e:
                                print(f"    parse error: {e}")
                                continue
                except Exception as e:
                    print(f"  read error on {port.device}: {e}")
                    time.sleep(0.05)

            # nothing found on this port
            try:
                ser.close()
            except:
                pass

        except Exception as e:
            print(f"Error opening {port.device}: {e}")
            try:
                if ser:
                    ser.close()
            except:
                pass
            continue

    print("\n❌ No joystick found!")
    sys.exit(1)

class FlightDisplay:
    def __init__(self):
        # --- Enhanced scene: sky gradient, sun, runway, hangars and 3D-ish plane ---
        pygame.init()
        self.width = 1024
        self.height = 768
        # main drawing surface
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.HWSURFACE)
        pygame.display.set_caption("3D Flight Simulator")

        # timing and font
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.fps_target = 60
        self.fps_history = []
        self.update_times = []

        # Flight state
        self.center_x = 512  # Adjusted for better center
        self.center_y = 512  # Adjusted for better center
        
        # Aircraft state
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        
        # Last raw joystick readings
        self.last_joy_x = float(self.center_x)
        self.last_joy_y = float(self.center_y)
        
        # Flight parameters
        self.roll_max = 45.0
        self.pitch_max = 30.0
        self.max_speed = 500.0
        self.min_speed = 100.0
        self.acceleration = 0.2
        self.drag = 0.98
        self.lift = 0.02
        self.gravity = 0.1
        self.roll_speed = 1.5
        self.pitch_speed = 1.0
        self.yaw_speed = 0.5
        
        # Camera
        self.camera_x = 0
        self.camera_y = 0
        self.camera_z = 0
        
        # World
        self.world_scale = 1.0
        self.terrain = []
        self.generate_terrain()
        
    def generate_terrain(self):
        # Simple terrain generation
        self.terrain = []
        for i in range(-10, 10):
            for j in range(-10, 10):
                self.terrain.append((i * 1000, j * 1000, 0))

    def update(self, x, y):
        # Store raw joystick values with smoothing
        self.last_joy_x = self.last_joy_x * 0.8 + float(x) * 0.2
        self.last_joy_y = self.last_joy_y * 0.8 + float(y) * 0.2
        
        # Calculate normalized input (-1 to 1) with inverted Y for natural control
        dx = (self.last_joy_x - self.center_x) / 511.5  # left/right for roll
        dy = -(self.last_joy_y - self.center_y) / 511.5  # up/down (inverted) for thrust
        
        # Apply deadzone
        deadzone = 0.1
        if abs(dx) < deadzone:
            dx = 0
        if abs(dy) < deadzone:
            dy = 0

        # Roll affects turning (banking turns the plane)
        target_roll = dx * self.roll_max
        # Pitch based on vertical speed
        target_pitch = dy * self.pitch_max

        # Smoothly update roll and pitch
        self.roll = self.roll * 0.9 + target_roll * 0.1
        self.pitch = self.pitch * 0.9 + target_pitch * 0.1
        
        # Convert to radians for calculations
        rad_roll = math.radians(self.roll)
        rad_pitch = math.radians(self.pitch)
        
        # Basic thrust from joystick Y position (up = forward)
        base_thrust = max(0, dy) * self.max_speed

        # Calculate directional forces
        # Roll causes turning (left/right movement)
        turn_rate = -math.sin(rad_roll) * base_thrust * 0.02
        
        # Forward movement reduced by pitch
        forward_speed = base_thrust * math.cos(abs(rad_pitch))
        
        # Vertical movement from pitch
        vertical_speed = math.sin(rad_pitch) * base_thrust

        # Update velocities with momentum
        self.velocity_x = self.velocity_x * 0.95 + turn_rate
        self.velocity_y = self.velocity_y * 0.95 + forward_speed * 0.1
        
        # Apply drag
        self.velocity_x *= self.drag
        self.velocity_y *= self.drag
        
        # Update world position
        self.pos_x += self.velocity_x
        self.pos_y += self.velocity_y
        
        # Update camera to follow plane
        self.camera_x = -self.pos_x * 0.1
        self.camera_y = -self.pos_y * 0.1

    def render(self):
        start_time = time.time()
        dt_ms = self.clock.get_time()
        dt = max(1.0/1000.0, dt_ms / 1000.0)
        
        # Clear screen with sky color
        self.screen.fill((135, 206, 235))  # Sky blue background
        
        # Calculate horizon line based on pitch
        horizon_y = self.height // 2 - self.pitch * 2
        
        # Draw sky gradient
        sky_top = (100, 200, 255)  # Lighter blue at top
        sky_bottom = (70, 130, 180)  # Darker blue at bottom
        horizon_y_int = max(0, min(int(horizon_y), self.height))
        for y in range(horizon_y_int):
            t = y / horizon_y_int if horizon_y_int > 0 else 0
            r = int(sky_top[0] * (1-t) + sky_bottom[0] * t)
            g = int(sky_top[1] * (1-t) + sky_bottom[1] * t)
            b = int(sky_top[2] * (1-t) + sky_bottom[2] * t)
            pygame.draw.line(self.screen, (r,g,b), (0, y), (self.width, y))
            
        # Draw ground
        ground_top = (100, 120, 60)  # Light ground color
        ground_bottom = (60, 80, 30)  # Dark ground color
        horizon_y_int = max(0, min(int(horizon_y), self.height))
        for y in range(horizon_y_int, self.height):
            t = (y - horizon_y_int) / (self.height - horizon_y_int) if horizon_y_int < self.height else 1
            r = int(ground_top[0] * (1-t) + ground_bottom[0] * t)
            g = int(ground_top[1] * (1-t) + ground_bottom[1] * t)
            b = int(ground_top[2] * (1-t) + ground_bottom[2] * t)
            pygame.draw.line(self.screen, (r,g,b), (0, y), (self.width, y))

        # Draw sun with parallax effect (moves opposite to plane movement)
        sun_x = self.width * 0.85 - self.pos_x * 0.02
        sun_y = self.height * 0.15 - self.pos_y * 0.02
        pygame.draw.circle(self.screen, (255, 230, 100), (int(sun_x), int(sun_y)), 36)
        
        # Draw clouds (simple circles with parallax)
        cloud_positions = [
            (200, 100), (400, 80), (600, 120),
            (100, 150), (300, 170), (700, 90), (900, 130)
        ]
        
        for cx, cy in cloud_positions:
            cloud_x = (cx - self.pos_x * 0.1) % (self.width + 200) - 100
            cloud_y = (cy - self.pos_y * 0.05) % (self.height // 2)
            if 0 <= cloud_x <= self.width and 0 <= cloud_y <= horizon_y:
                s = pygame.Surface((120, 60), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (255, 255, 255, 200), (0, 0, 120, 60))
                pygame.draw.ellipse(s, (255, 255, 255, 200), (30, 10, 80, 50))
                pygame.draw.ellipse(s, (255, 255, 255, 200), (60, 0, 60, 60))
                self.screen.blit(s, (int(cloud_x - 60), int(cloud_y - 30)))
        
        # Draw ground features (trees, buildings, etc.)
        for i in range(-5, 20):
            # Trees
            tree_x = (i * 200 - self.pos_x * 0.5) % (self.width + 400) - 200
            if 0 <= tree_x <= self.width:
                tree_base = int(horizon_y + 20)
                pygame.draw.rect(self.screen, (139, 69, 19), (int(tree_x) - 5, tree_base, 10, 30))
                pygame.draw.polygon(self.screen, (34, 139, 34), [
                    (int(tree_x) - 25, tree_base),
                    (int(tree_x) + 25, tree_base),
                    (int(tree_x), tree_base - 50)
                ])
            
            # Buildings
            if i % 3 == 0:
                bldg_x = (i * 300 - self.pos_x * 0.3) % (self.width + 600) - 300
                if 0 <= bldg_x <= self.width:
                    bldg_width = 60 + (i * 7) % 40
                    bldg_height = 100 + (i * 13) % 150
                    bldg_base = int(horizon_y + 5)
                    
                    # Building
                    pygame.draw.rect(self.screen, (70, 70, 70), 
                                  (int(bldg_x), bldg_base - bldg_height, 
                                   bldg_width, bldg_height))
                    
                    # Windows
                    for wy in range(5, bldg_height - 10, 15):
                        for wx in range(5, bldg_width - 10, 15):
                            if random.random() > 0.3:  # Random lit windows
                                pygame.draw.rect(self.screen, (255, 255, 0), 
                                              (int(bldg_x) + wx, bldg_base - bldg_height + wy, 5, 8))
        
        # Draw horizon line
        pygame.draw.line(self.screen, (0, 0, 0), (0, horizon_y), (self.width, horizon_y), 2)

        # Draw plane (centered on screen, but with movement effects)
        cx = self.width // 2
        cy = self.height // 2
        body_length = 100
        body_w = 16
        wing_span = 180
        
        # Calculate plane's visual tilt based on roll and pitch
        roll_rad = math.radians(self.roll)
        pitch_rad = math.radians(self.pitch)
        
        # Draw shadow (moves with plane)
        shadow = pygame.Surface((wing_span + 40, 60), pygame.SRCALPHA)
        shadow_y_offset = 40 + abs(self.pitch)  # Shadow moves down when pitching up/down
        shadow_scale = 1.0 - abs(self.roll) / 90.0  # Shadow scales with roll
        shadow_width = int((wing_span + 40) * (0.7 + 0.3 * shadow_scale))
        shadow = pygame.transform.scale(shadow, (shadow_width, 30))
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
        shadow_x = cx - shadow_width // 2 + math.sin(roll_rad) * 30
        shadow_y = cy + shadow_y_offset
        self.screen.blit(shadow, (int(shadow_x), int(shadow_y)))
        
        # Draw plane body
        def rotate_point(x, y, angle, center_x=0, center_y=0):
            x -= center_x
            y -= center_y
            new_x = x * math.cos(angle) - y * math.sin(angle)
            new_y = x * math.sin(angle) + y * math.cos(angle)
            return (new_x + center_x, new_y + center_y)
        
        # Draw wings with banking effect
        wing_color = (100, 100, 120)
        
        # Left wing
        wing_points = [
            (cx - 10, cy),
            (cx - wing_span//2, cy + 5),
            (cx - wing_span//2 + 20, cy + 20),
            (cx - 6, cy + 8)
        ]
        wing_points = [rotate_point(x, y, roll_rad * 0.5, cx, cy) for x, y in wing_points]
        pygame.draw.polygon(self.screen, wing_color, wing_points)
        
        # Right wing
        wing_points = [
            (cx + 10, cy),
            (cx + wing_span//2, cy + 5),
            (cx + wing_span//2 - 20, cy + 20),
            (cx + 6, cy + 8)
        ]
        wing_points = [rotate_point(x, y, -roll_rad * 0.5, cx, cy) for x, y in wing_points]
        pygame.draw.polygon(self.screen, wing_color, wing_points)
        
        # Draw body with pitch effect
        body_rect = pygame.Rect(0, 0, body_w, body_length)
        body_rect.center = (cx, cy + math.sin(pitch_rad) * 10)
        body_surface = pygame.Surface((body_w, body_length), pygame.SRCALPHA)
        pygame.draw.ellipse(body_surface, (80, 80, 100), (0, 0, body_w, body_length))
        
        # Tilt body with roll
        body_surface = pygame.transform.rotate(body_surface, -self.roll * 0.8)
        self.screen.blit(body_surface, 
                        (cx - body_surface.get_width() // 2, 
                         cy - body_surface.get_height() // 2 + math.sin(pitch_rad) * 10))
        
        # Draw tail
        tail_points = [
            (cx - 6, cy - body_length//3),
            (cx + 6, cy - body_length//3),
            (cx, cy - body_length//2)
        ]
        tail_points = [rotate_point(x, y, roll_rad * 0.3, cx, cy) for x, y in tail_points]
        pygame.draw.polygon(self.screen, (90, 90, 110), tail_points)
        
        # Draw cockpit
        pygame.draw.ellipse(self.screen, (20, 60, 150), 
                          (cx - 12, cy - body_length//3 - 10, 24, 20))
        
        # Draw engine exhaust (more visible when accelerating)
        speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        flame_size = min(30, max(10, speed * 0.1))
        flame_color = (255, 140 + random.randint(0, 50), 0)  # Flickering effect
        flame_rect = pygame.Rect(cx - 8, cy + body_length//2, 16, flame_size)
        # draw on the main screen surface
        pygame.draw.ellipse(self.screen, flame_color, flame_rect)

        # HUD
        pygame.draw.line(self.screen, (255, 0, 0), (400 - 20, 300), (400 + 20, 300), 3)
        pygame.draw.line(self.screen, (255, 0, 0), (400, 300 - 20), (400, 300 + 20), 3)

        # Show debug
        self.show_debug_info(self.roll, self.pitch)

        # Flip and timing
        pygame.display.flip()
        self.clock.tick(self.fps_target)

        # Track frame time
        self.update_times.append(time.time() - start_time)
        if len(self.update_times) > 60:
            self.update_times.pop(0)
            
    def show_debug_info(self, roll, pitch):
        # Calculate speed
        speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        
        # Show flight data with better formatting
        debug_lines = [
            f"Position: X:{int(self.pos_x)} Y:{int(self.pos_y)}",
            f"Speed: {speed:.1f} units/s",
            f"Attitude: Roll:{roll:5.1f}° Pitch:{pitch:5.1f}°",
            f"Velocity: X:{self.velocity_x:5.1f} Y:{self.velocity_y:5.1f}",
            f"FPS: {int(self.clock.get_fps())}"
        ]
        
        # Render debug text with background for better readability
        for i, line in enumerate(debug_lines):
            text_surface = self.font.render(line, True, (255, 255, 255))
            # Add semi-transparent background
            bg_rect = pygame.Rect(10, 10 + i * 25, text_surface.get_width() + 10, text_surface.get_height() + 2)
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 128))  # Semi-transparent black
            self.screen.blit(s, bg_rect)
            self.screen.blit(text_surface, (15, 12 + i * 25))

def main():
    # Initialize hardware
    print("🔍 Searching for joystick...")
    ser = find_bluetooth_port()
    ser.reset_input_buffer()  # Start fresh
    
    # Initialize display
    display = FlightDisplay()
    
    running = True
    last_time = time.time()
    
    # Default joystick position (center)
    joy_x = display.center_x
    joy_y = display.center_y
    
    while running:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Read joystick data
        if ser.in_waiting:
            try:
                # Read all available data
                data = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
                # Process each line
                lines = [line.strip() for line in data.split('\n') if line.strip()]
                
                # Process the most recent complete line
                if lines:
                    last_line = lines[-1]
                    if 'X:' in last_line and 'Y:' in last_line:
                        try:
                            # Extract X and Y values
                            parts = last_line.split(',')
                            if len(parts) >= 2:
                                x_str = parts[0].split(':')[-1].strip()
                                y_str = parts[1].split(':')[-1].strip()
                                joy_x = int(x_str)
                                joy_y = int(y_str)
                                
                                # Update display with joystick position
                                display.update(joy_x, joy_y)
                                
                                # Print debug info (uncomment for debugging)
                                # print(f"Joystick - X: {joy_x}, Y: {joy_y}")
                                
                        except (ValueError, IndexError) as e:
                            print(f"Error parsing joystick data: {e}")
                            continue
            except Exception as e:
                print(f"Serial read error: {e}")
                # Try to recover by resetting the buffer
                try:
                    ser.reset_input_buffer()
                except:
                    pass
        
        # Update and render the game
        display.render()
        
        # Cap the frame rate
        display.clock.tick(60)
    
    # Cleanup
    ser.close()
    pygame.quit()

if __name__ == "__main__":
    main()
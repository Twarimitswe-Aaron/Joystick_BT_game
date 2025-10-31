import serial
import serial.tools.list_ports
import time
import pygame
import math
import sys

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
        self.width = 800
        self.height = 600
        # main drawing surface
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("3D Flight Simulator")

        # timing and font
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.fps_target = 120
        self.fps_history = []
        self.update_times = []

        # Initialize flight state
        self.center_x = 448
        self.center_y = 461
        self.current_x = float(self.center_x)
        self.current_y = float(self.center_y)
        self.roll_max = 45
        self.pitch_max = 30

    def update(self, x, y):
        # External update from serial parser
        self.current_x = float(x)
        self.current_y = float(y)

    def render(self):
        start_time = time.time()

        # Compute angles from current readings
        roll = ((self.current_x - self.center_x) * self.roll_max) / 511.5
        pitch = ((self.current_y - self.center_y) * self.pitch_max) / 511.5

        width = self.width
        height = self.height

        # Sky gradient (top -> bottom)
        top = (250, 200, 120)
        mid = (135, 206, 235)
        bottom = (100, 150, 200)
        for i in range(height):
            t = i / height
            if t < 0.5:
                mix = t * 2
                color = (
                    int(top[0] * (1 - mix) + mid[0] * mix),
                    int(top[1] * (1 - mix) + mid[1] * mix),
                    int(top[2] * (1 - mix) + mid[2] * mix)
                )
            else:
                mix = (t - 0.5) * 2
                color = (
                    int(mid[0] * (1 - mix) + bottom[0] * mix),
                    int(mid[1] * (1 - mix) + bottom[1] * mix),
                    int(mid[2] * (1 - mix) + bottom[2] * mix)
                )
            pygame.draw.line(self.screen, color, (0, i), (width, i))

        # Sun
        sun_x = width * 0.85
        sun_y = height * 0.15 + pitch * 0.5
        pygame.draw.circle(self.screen, (255, 230, 100), (int(sun_x), int(sun_y)), 36)
        for r in (50, 70):
            s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 230, 100, 12), (r, r), r)
            self.screen.blit(s, (sun_x - r, sun_y - r))

        # Hangars/dishes
        base_y = height * 0.45 - pitch * 0.3
        roll_shift = math.tan(math.radians(roll)) * 80
        for i in range(3):
            x = 120 - i*60 - roll_shift
            y = base_y + i*18
            pygame.draw.rect(self.screen, (110,110,110), (x, y, 80, 40))
            pygame.draw.polygon(self.screen, (90,90,90), [(x, y), (x+40, y-20), (x+80, y)])
        for i in range(3):
            x = width - 200 + i*60 - roll_shift
            y = base_y + i*22
            pygame.draw.polygon(self.screen, (140,140,140), [(x,y),(x+20,y-20),(x+40,y)])
            pygame.draw.circle(self.screen, (60,60,60), (int(x+20), int(y-8)), 8)

        # Runway
        mid_x = width // 2
        horizon_y = height * 0.45 - pitch * (height / (2 * self.pitch_max))
        roll_rad = math.radians(roll)
        vanishing_offset = math.tan(roll_rad) * width * 0.6
        left_vanish_x = mid_x - vanishing_offset
        right_vanish_x = mid_x + vanishing_offset
        near_width = width * 0.6
        far_width = width * 0.06
        near_y = height * 0.85
        far_y = max(40, horizon_y)
        left_near = (mid_x - near_width/2, near_y)
        right_near = (mid_x + near_width/2, near_y)
        left_far = (left_vanish_x - far_width/2, far_y)
        right_far = (right_vanish_x + far_width/2, far_y)
        pygame.draw.polygon(self.screen, (55,55,60), [left_near, right_near, right_far, left_far])
        num_dashes = 12
        for i in range(num_dashes):
            t1 = i / num_dashes
            t2 = (i + 0.6) / num_dashes
            x1 = left_near[0] + (left_far[0] - left_near[0]) * t1
            x2 = left_near[0] + (left_far[0] - left_near[0]) * t2
            y1 = near_y + (far_y - near_y) * t1
            y2 = near_y + (far_y - near_y) * t2
            cx1 = (x1 + (right_near[0] + (right_far[0] - right_near[0]) * t1)) / 2
            cx2 = (x2 + (right_near[0] + (right_far[0] - right_near[0]) * t2)) / 2
            pygame.draw.line(self.screen, (240,240,240), (cx1, y1), (cx2, y2), 4)
        pygame.draw.line(self.screen, (200,200,200), left_near, left_far, 2)
        pygame.draw.line(self.screen, (200,200,200), right_near, right_far, 2)

        # Plane (simple shapes)
        cx = width//2
        cy = int(height*0.62)
        body_length = 140
        body_w = 18
        wing_span = 200
        fusage_rect = pygame.Rect(0,0, body_w, body_length)
        fusage_rect.center = (cx, cy)
        pygame.draw.ellipse(self.screen, (80,80,80), fusage_rect)
        wing_color = (120,120,120)
        left_wing = [(cx - 10, cy), (cx - wing_span//2, cy + 10), (cx - wing_span//2 + 20, cy + 24), (cx - 6, cy + 6)]
        right_wing = [(cx + 10, cy), (cx + wing_span//2, cy + 10), (cx + wing_span//2 - 20, cy + 24), (cx + 6, cy + 6)]
        def tilt_point(p):
            dx = p[0] - cx
            dy = p[1] - cy
            angle = math.radians(roll * 0.6)
            rx = dx * math.cos(angle) - dy * math.sin(angle)
            ry = dx * math.sin(angle) + dy * math.cos(angle)
            return (cx + rx, cy + ry)
        left_wing = [tilt_point(p) for p in left_wing]
        right_wing = [tilt_point(p) for p in right_wing]
        pygame.draw.polygon(self.screen, wing_color, left_wing)
        pygame.draw.polygon(self.screen, wing_color, right_wing)
        tail = [(cx-6, cy+body_length//4), (cx+6, cy+body_length//4), (cx, cy+body_length//4 - 30)]
        pygame.draw.polygon(self.screen, (100,100,100), tail)
        pygame.draw.ellipse(self.screen, (20,60,120), (cx-14, cy-40, 28, 22))
        flame_color = (255,140,0) if pitch < 0 else (200,80,0)
        flame_rect = pygame.Rect(cx-10, cy+body_length//2, 20, 26)
        pygame.draw.ellipse(self.screen, flame_color, flame_rect)
        shadow = pygame.Surface((220,70), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0,0,0,90), shadow.get_rect())
        self.screen.blit(shadow, (cx-110, cy+30))

        # HUD
        pygame.draw.line(self.screen, (255, 0, 0), (400 - 20, 300), (400 + 20, 300), 3)
        pygame.draw.line(self.screen, (255, 0, 0), (400, 300 - 20), (400, 300 + 20), 3)

        # Show debug
        self.show_debug_info(roll, pitch)

        # Flip and timing
        pygame.display.flip()
        self.clock.tick(self.fps_target)

        # Track frame time
        self.update_times.append(time.time() - start_time)
        if len(self.update_times) > 60:
            self.update_times.pop(0)
            
    def show_debug_info(self, roll, pitch):
        # Show position and angles
        text = self.font.render(
            f"X: {self.current_x}  Y: {self.current_y}", True, (0, 0, 0))
        self.screen.blit(text, (10, 10))
        
        text = self.font.render(
            f"Roll: {roll:.1f}°  Pitch: {pitch:.1f}°", True, (0, 0, 0))
        self.screen.blit(text, (10, 50))
        
        # Show FPS and timing
        fps = self.clock.get_fps()
        self.fps_history.append(fps)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)
        
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        avg_update = sum(self.update_times) / len(self.update_times) * 1000 if self.update_times else 0
        
        text = self.font.render(
            f"FPS: {int(avg_fps)} Frame Time: {avg_update:.1f}ms", True, (0, 0, 0))
        self.screen.blit(text, (10, 90))

def main():
    # Initialize hardware
    print("🔍 Searching for joystick...")
    ser = find_bluetooth_port()
    ser.reset_input_buffer()  # Start fresh
    
    # Initialize display
    display = FlightDisplay()
    
    running = True
    last_data = 0
    frame_count = 0
    
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        # Read all available serial data with non-blocking approach
        if ser.in_waiting:
            try:
                # Read all available data at once
                data = ser.read(ser.in_waiting).decode(errors='ignore')
                lines = data.splitlines()
                
                # Process only the most recent complete line
                for line in reversed(lines):
                    if "X:" in line and "Y:" in line:
                        try:
                            x_part, y_part = line.split(",")
                            x = int(''.join(c for c in x_part if c.isdigit()))
                            y = int(''.join(c for c in y_part if c.isdigit()))
                            
                            if 0 <= x <= 1023 and 0 <= y <= 1023:
                                display.update(x, y)
                                last_data = time.time()
                                break
                        except ValueError:
                            continue
                            
            except Exception as e:
                print(f"Read error: {e}")
        
        # Render frame
        display.render()
        
        # Maintain high frame rate
        display.clock.tick(165)  # Target 165 FPS for smooth motion
        
        frame_count += 1
        if frame_count % 60 == 0:  # Log every 60 frames
            data_age = time.time() - last_data
            if data_age > 0.1:  # More than 100ms old
                print(f"⚠️ Data age: {data_age*1000:.0f}ms")
    
    # Cleanup
    ser.close()
    pygame.quit()

if __name__ == "__main__":
    main()
import serial
import serial.tools.list_ports
import time
import re
import pygame
import sys
import math
import random
from pygame.locals import *
from pygame import gfxdraw

# ==============================
# CONSTANTS
# ==============================
BAUD = 38400
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
BLACK = (0, 0, 20)
WHITE = (255, 255, 255)
BLUE = (100, 150, 255)

# ==============================
# SERIAL COMMUNICATION
# ==============================
def find_active_port():
    """Scan for active COM port with expected data format in descending order"""
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("❌ No COM ports found!")
        return None

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

    # Try preferred ports first (Bluetooth / HC-05 / Arduino)
    preferred_keywords = ("HC-05", "Bluetooth", "Arduino", "Serial")
    def port_priority(p):
        desc = (p.description or "").lower()
        for kw in preferred_keywords:
            if kw.lower() in desc:
                return 0
        return 1
    ports.sort(key=port_priority)  # Prioritize but keep descending order

    # Detection strategy: try each port, require multiple valid readings
    for port in ports:
        print(f"\n📡 Testing {port.device} ({port.description})...")
        ser = None
        try:
            # Open with short timeout for faster detection
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
                        x, y = parse_xy(s)
                        if x is not None:  # Successfully parsed
                            valid_count += 1
                            if valid_count >= 2:  # Require 2 valid readings
                                print(f"✅ Found joystick on {port.device}")
                                print(f"   Last reading: X={x}, Y={y}")
                                return ser
                
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
    return None

def parse_xy(line):
    """Optimized parsing of X and Y values."""
    # Single regex pattern for both formats
    pattern = r"(?:X[:=]\s*(\d+))[^\d]*(?:Y[:=]\s*(\d+))"
    match = re.search(pattern, line)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Fallback: find any 2-4 digit numbers
    numbers = re.findall(r'\b\d{2,4}\b', line)
    return (int(numbers[0]), int(numbers[1])) if len(numbers) >= 2 else (None, None)

# ==============================
# STAR FIELD OPTIMIZATIONS
# ==============================
class StarField:
    """Optimized star field management."""
    
    def __init__(self, num_stars, width, height):
        self.stars = []
        self.width = width
        self.height = height
        self.star_cache = {}
        self._initialize_stars(num_stars)
    
    def _initialize_stars(self, num_stars):
        """Initialize stars with optimized distribution."""
        for _ in range(num_stars):
            size = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
            x = random.randint(0, self.width)
            y = random.randint(-self.height * 3, self.height)
            speed = random.uniform(30.0, 100.0) * (1 + size * 0.3)
            brightness = random.uniform(0.7, 1.0)
            self.stars.append((x, y, speed, size, brightness))
    
    def update(self, speed_factor, dt):
        """Batch update stars with recycling."""
        for i, (x, y, speed, size, brightness) in enumerate(self.stars):
            # Move stars
            y += speed * (1 + size * 0.3) * dt * speed_factor
            
            # Recycle off-screen stars
            if y > self.height + 20:
                y = random.randint(-50, -10)
                x = random.randint(0, self.width)
                # Occasionally change star properties
                if random.random() < 0.2:
                    size = random.choices([1, 2, 3], weights=[6, 3, 1])[0]
                    brightness = random.uniform(0.7, 1.0)
            
            self.stars[i] = (x, y, speed, size, brightness)
    
    def draw(self, surface):
        """Optimized star drawing with caching."""
        for x, y, _, size, brightness in self.stars:
            cache_key = (size, int(brightness * 10))
            
            if cache_key not in self.star_cache:
                star_surf = self._create_star_surface(size, brightness)
                self.star_cache[cache_key] = star_surf
            
            star_surf = self.star_cache[cache_key]
            surface.blit(star_surf, (x - star_surf.get_width()//2, y - star_surf.get_height()//2))
    
    def _create_star_surface(self, size, brightness):
        """Create a cached star surface."""
        s = size * 2 + 2
        star_surf = pygame.Surface((s, s), pygame.SRCALPHA)
        
        # Calculate color with brightness
        b = min(255, int(200 * brightness + 55))
        g = min(255, int(180 * brightness + 75))
        r = min(255, int(190 * brightness + 65))
        
        # Draw glow for larger stars
        if size > 1:
            pygame.draw.circle(star_surf, (r, g, b, 100), (s//2, s//2), size + 1)
        
        # Draw star
        pygame.draw.circle(star_surf, (r, g, b), (s//2, s//2), size)
        return star_surf

# ==============================
# JET RENDERING
# ==============================
def draw_jet(surface, x, y, angle, size=30):
    """Optimized jet rendering with pre-computed surfaces."""
    if not hasattr(draw_jet, 'cache'):
        draw_jet.cache = {}
    
    # Cache key based on size and angle (quantized for efficiency)
    angle_deg = int(math.degrees(angle) / 5) * 5  # Quantize to 5-degree steps
    cache_key = (size, angle_deg)
    
    if cache_key not in draw_jet.cache:
        jet_surface = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
        
        # Pre-computed jet points
        points = [
            (size, 0),                     # Nose
            (0, size),                     # Left wing tip
            (size//2, size),               # Left wing root
            (size//2, size*1.5),           # Left tail
            (size*1.5, size*1.5),          # Right tail
            (size*1.5, size),              # Right wing root
            (size*2, size),                # Right wing tip
        ]
        
        # Draw jet body
        pygame.draw.polygon(jet_surface, (200, 200, 200), points)
        
        # Draw cockpit
        pygame.draw.circle(jet_surface, (100, 180, 255), 
                          (int(size*0.8), int(size*0.8)), size//4)
        
        # Draw engine glow
        glow = pygame.Surface((size//2, size//2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 100, 0, 180), (size//4, size//4), size//2)
        jet_surface.blit(glow, (size//2, size*1.2), special_flags=pygame.BLEND_ADD)
        
        # Rotate and cache
        rotated_jet = pygame.transform.rotate(jet_surface, angle_deg)
        draw_jet.cache[cache_key] = rotated_jet
    
    # Get cached surface and draw
    rotated_jet = draw_jet.cache[cache_key]
    rect = rotated_jet.get_rect(center=(x, y))
    surface.blit(rotated_jet, rect.topleft)
    
    return rect

# ==============================
# HUD MANAGEMENT
# ==============================
class HUD:
    """Optimized HUD rendering."""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = pygame.font.SysFont('Arial', 24, bold=True)
        
        # Pre-render static elements
        self.speed_label = self.font.render('Speed:', True, WHITE)
        self.score_label = self.font.render('Score:', True, WHITE)
        
        # Create HUD background
        self.background = pygame.Surface((width, 40), pygame.SRCALPHA)
        self.background.fill((0, 0, 0, 128))
    
    def draw(self, surface, speed, score):
        """Draw HUD with current values."""
        surface.blit(self.background, (0, 0))
        
        # Render dynamic values
        speed_text = self.font.render(f"{abs(speed):.1f}", True, WHITE)
        score_text = self.font.render(f"{int(score)}", True, WHITE)
        
        # Blit all elements
        surface.blit(self.speed_label, (20, 10))
        surface.blit(speed_text, (100, 10))
        surface.blit(self.score_label, (self.width - 150, 10))
        surface.blit(score_text, (self.width - 80, 10))

# ==============================
# MAIN GAME LOOP
# ==============================
def start_joystick_view(serial_port):
    """Optimized main game loop with enhanced physics."""
    # Initialize pygame with performance flags
    pygame.init()
    flags = pygame.DOUBLEBUF | pygame.HWSURFACE
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
    pygame.display.set_caption("Jet Fighter Simulator")
    
    # Limit events for better performance
    pygame.event.set_allowed([QUIT, KEYDOWN])
    
    # Initialize game objects
    stars = StarField(200, WINDOW_WIDTH, WINDOW_HEIGHT)
    hud = HUD(WINDOW_WIDTH, WINDOW_HEIGHT)
    clock = pygame.time.Clock()
    
    # Enhanced jet state with physics parameters
    jet_state = {
        'x': WINDOW_WIDTH // 2,
        'y': WINDOW_HEIGHT * 2 // 3,
        'z': 0.0,
        'roll': 0.0,  # banking angle
        'pitch': 0.0,  # nose up/down
        'yaw': 0.0,   # heading
        'velocity_x': 0.0,
        'velocity_y': 0.0,
        'velocity_z': 0.0,
        'speed': 0.0,  # Add speed tracking
        'size': 30,
        # Flight parameters
        'roll_max': 45.0,
        'pitch_max': 30.0,
        'max_speed': 500.0,
        'min_speed': 100.0
    }
    
    # Game state
    game_state = {
        'score': 0,
        'x_val': 512,
        'y_val': 512,
        'running': True
    }
    
    # Joystick visualization
    joy_center = (80, WINDOW_HEIGHT - 80)
    
    # Performance tracking
    last_time = time.time()
    frame_count = 0
    fps_update_time = last_time
    
    print("🎮 Jet Fighter Simulator started (Optimized)")
    
    # Main game loop
    while game_state['running']:
        current_time = time.time()
        dt = min(current_time - last_time, 0.1)
        last_time = current_time
        
        frame_count += 1
        if current_time - fps_update_time >= 1.0:
            fps = frame_count / (current_time - fps_update_time)
            if fps < 55:
                print(f"Performance: {fps:.1f} FPS")
            frame_count = 0
            fps_update_time = current_time
        
        # Process events
        game_state['running'] = _handle_events(serial_port, game_state, jet_state)
        
        # Update game state
        _update_game_state(serial_port, game_state, jet_state, dt)
        
        # Render frame
        _render_frame(screen, stars, hud, game_state, jet_state, joy_center, dt)
        
        # Cap frame rate
        clock.tick(60)
    
    serial_port.close()
    pygame.quit()
    print("🔚 Jet Fighter Simulator ended.")

def _handle_events(serial_port, game_state, jet_state):
    """Handle pygame events."""
    for event in pygame.event.get():
        if event.type == QUIT:
            return False
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                return False
            elif event.key == K_r:
                # Reset game state
                jet_state.update({
                    'x': WINDOW_WIDTH // 2,
                    'y': WINDOW_HEIGHT * 2 // 3,
                    'angle': 0.0,
                    'speed': 0.0
                })
                game_state['score'] = 0
    return True

def _update_game_state(serial_port, game_state, jet_state, dt):
    """Update game state based on serial input with immediate response."""
    try:
        # Process all available serial data (non-blocking)
        if serial_port.in_waiting > 0:
            data = serial_port.read(serial_port.in_waiting).decode(errors='ignore')
            lines = data.splitlines()
            
            # Process most recent complete line
            for line in reversed(lines):
                x, y = parse_xy(line)
                if x is not None and y is not None:
                    game_state['x_val'], game_state['y_val'] = x, y
                    break
    except Exception as e:
        if "timeout" not in str(e).lower():
            print(f"Serial error: {e}")
    
    # Calculate normalized controls (-1 to 1)
    roll = (game_state['x_val'] - 512) / 511.5  # left/right controls roll/heading
    pitch = -(game_state['y_val'] - 512) / 511.5  # up/down controls pitch/elevation
    
    # Apply deadzone
    deadzone = 0.1
    roll = 0 if abs(roll) < deadzone else roll
    pitch = 0 if abs(pitch) < deadzone else pitch
    
    # Update aircraft physics
    # Roll affects turning (banking turns the plane)
    target_roll = roll * jet_state['roll_max']
    jet_state['roll'] = jet_state['roll'] * 0.9 + target_roll * 0.1
    
    # Pitch controls vertical movement and affects speed
    target_pitch = pitch * jet_state['pitch_max']
    jet_state['pitch'] = jet_state['pitch'] * 0.9 + target_pitch * 0.1
    
    # Convert angles to radians
    roll_rad = math.radians(jet_state['roll'])
    pitch_rad = math.radians(jet_state['pitch'])
    
    # Basic thrust (more when pulling back/up on stick)
    base_thrust = max(0, pitch) * jet_state['max_speed']
    
    # Turn rate based on roll angle and speed
    turn_rate = -math.sin(roll_rad) * base_thrust * 0.02
    
    # Forward speed reduced by pitch angle
    forward_speed = base_thrust * math.cos(abs(pitch_rad))
    
    # Update velocities with momentum
    jet_state['velocity_x'] = jet_state['velocity_x'] * 0.95 + turn_rate
    jet_state['velocity_y'] = jet_state['velocity_y'] * 0.95 + forward_speed * 0.1
    
    # Apply drag
    drag = 0.98
    jet_state['velocity_x'] *= drag
    jet_state['velocity_y'] *= drag
    
    # Update position with delta time scaling
    move_scale = 60.0 * dt  # Scale movement by frame time
    jet_state['x'] += jet_state['velocity_x'] * move_scale
    jet_state['y'] += jet_state['velocity_y'] * move_scale
    
    # World wrapping (loop around screen edges)
    jet_state['x'] = jet_state['x'] % WINDOW_WIDTH
    jet_state['y'] = max(50, min(WINDOW_HEIGHT - 50, jet_state['y']))
    
    # Update speed and score based on movement
    jet_state['speed'] = math.sqrt(jet_state['velocity_x']**2 + jet_state['velocity_y']**2)
    game_state['score'] += jet_state['speed'] * dt

def _render_frame(screen, stars, hud, game_state, jet_state, joy_center, dt):
    """Render a single frame."""
    screen.fill(BLACK)
    
    # Update and draw stars
    speed_factor = 1.0 + abs(jet_state['speed']) * 0.3
    stars.update(speed_factor, dt * 60)
    stars.draw(screen)
    
    # Draw jet with roll angle
    draw_jet(screen, int(jet_state['x']), int(jet_state['y']), 
             jet_state['roll'], jet_state['size'])
    
    # Draw HUD
    hud.draw(screen, jet_state['speed'], game_state['score'])
    
    # Draw joystick visualization
    joy_x = int(joy_center[0] + ((game_state['x_val'] - 512) / 512.0 * 20))
    joy_y = int(joy_center[1] + ((game_state['y_val'] - 512) / 512.0 * 20))
    
    pygame.draw.circle(screen, (100, 100, 100, 100), joy_center, 40, 1)
    pygame.draw.circle(screen, WHITE, (joy_x, joy_y), 10)
    
    pygame.display.flip()

# ==============================
# MAIN EXECUTION
# ==============================
if __name__ == "__main__":
    ser = find_active_port()
    if ser:
        start_joystick_view(ser)
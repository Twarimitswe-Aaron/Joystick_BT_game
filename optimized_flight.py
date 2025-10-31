import pygame
import math
import random
import serial
import serial.tools.list_ports
import time
import sys

# ==============================
# Constants and Initialization
# ==============================
WINDOW_WIDTH, WINDOW_HEIGHT = 1024, 768
FPS = 60
BAUD_RATE = 38400

# Colors
SKY_COLOR = (135, 206, 235)
GROUND_COLOR = (100, 120, 60)
SUN_COLOR = (255, 230, 100)
PLANE_BODY = (80, 80, 100)
PLANE_WINGS = (100, 100, 120)

# Flight parameters
ROLL_MAX = 45.0
PITCH_MAX = 30.0
MAX_SPEED = 5.0
MIN_SPEED = 1.0
ACCELERATION = 0.05
DRAG = 0.98
LIFT = 0.02
GRAVITY = 0.1

class FlightSimulator:
    def __init__(self):
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), 
                                           pygame.DOUBLEBUF | pygame.HWSURFACE)
        pygame.display.set_caption("Optimized Flight Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24, bold=True)
        
        # Game state
        self.running = True
        self.clock = pygame.time.Clock()
        
        # Flight state
        self.roll = 0.0
        self.pitch = 0.0
        self.pos_x = WINDOW_WIDTH // 2
        self.pos_y = WINDOW_HEIGHT // 2
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.camera_x = 0
        self.camera_y = 0
        
        # Joystick values (centered)
        self.joystick_x = 512
        self.joystick_y = 512
        
        # Pre-render surfaces
        self._init_surfaces()
        
    def _init_surfaces(self):
        """Pre-render static surfaces for better performance."""
        # Create a surface for the plane
        self.plane_surface = pygame.Surface((100, 60), pygame.SRCALPHA)
        
        # Draw plane body
        pygame.draw.ellipse(self.plane_surface, PLANE_BODY, (30, 10, 40, 40))
        
        # Draw wings
        wing_points = [(0, 30), (30, 25), (70, 25), (100, 30), (70, 35), (30, 35)]
        pygame.draw.polygon(self.plane_surface, PLANE_WINGS, wing_points)
        
        # Draw tail
        pygame.draw.polygon(self.plane_surface, PLANE_WINGS, 
                          [(70, 15), (90, 0), (95, 5), (75, 25)])
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update(self):
        # Calculate delta time for smooth movement
        dt = self.clock.get_time() / 16.0  # Normalize to ~60 FPS
        
        # Get joystick input (normalized -1 to 1)
        dx = (self.joystick_x - 512) / 512.0
        dy = (self.joystick_y - 512) / 512.0
        
        # Apply deadzone
        deadzone = 0.1
        if abs(dx) < deadzone: dx = 0
        if abs(dy) < deadzone: dy = 0
        
        # Update roll and pitch based on joystick
        target_roll = -dx * ROLL_MAX
        target_pitch = -dy * PITCH_MAX
        
        # Smooth interpolation
        self.roll += (target_roll - self.roll) * 0.1
        self.pitch += (target_pitch - self.pitch) * 0.08
        
        # Convert to radians for calculations
        rad_roll = math.radians(self.roll)
        rad_pitch = math.radians(self.pitch)
        
        # Calculate movement
        speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        if speed < 0.1: speed = 0.1
        
        # Update velocities
        self.velocity_x += math.sin(rad_roll) * ACCELERATION * dt
        self.velocity_y += (math.sin(rad_pitch) * ACCELERATION - GRAVITY) * dt
        
        # Apply drag
        self.velocity_x *= DRAG
        self.velocity_y *= DRAG
        
        # Limit speed
        speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        if speed > MAX_SPEED:
            self.velocity_x = (self.velocity_x / speed) * MAX_SPEED
            self.velocity_y = (self.velocity_y / speed) * MAX_SPEED
        
        # Update position
        self.pos_x += self.velocity_x * dt * 10
        self.pos_y += self.velocity_y * dt * 10
        
        # Keep plane in bounds
        self.pos_x = max(0, min(WINDOW_WIDTH, self.pos_x))
        self.pos_y = max(0, min(WINDOW_HEIGHT, self.pos_y))
        
        # Update camera (smooth follow)
        self.camera_x += ((WINDOW_WIDTH // 2 - self.pos_x) - self.camera_x) * 0.1
        self.camera_y += ((WINDOW_HEIGHT // 2 - self.pos_y) - self.camera_y) * 0.1
    
    def draw(self):
        # Clear screen
        self.screen.fill(SKY_COLOR)
        
        # Draw ground
        horizon_y = WINDOW_HEIGHT // 2 - self.pitch * 2
        pygame.draw.rect(self.screen, GROUND_COLOR, 
                        (0, horizon_y, WINDOW_WIDTH, WINDOW_HEIGHT - horizon_y))
        
        # Draw sun (with parallax)
        sun_x = WINDOW_WIDTH * 0.85 - self.camera_x * 0.1
        sun_y = WINDOW_HEIGHT * 0.15 - self.camera_y * 0.1
        pygame.draw.circle(self.screen, SUN_COLOR, (int(sun_x), int(sun_y)), 36)
        
        # Draw plane (pre-rendered surface with rotation)
        rotated_plane = pygame.transform.rotate(self.plane_surface, -self.roll)
        plane_rect = rotated_plane.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + self.pitch))
        self.screen.blit(rotated_plane, plane_rect.topleft)
        
        # Draw HUD
        speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        speed_text = self.font.render(f"Speed: {speed:.1f}", True, (255, 255, 255))
        alt_text = self.font.render(f"Alt: {int(WINDOW_HEIGHT - self.pos_y)}", True, (255, 255, 255))
        
        # Semi-transparent HUD background
        hud_surface = pygame.Surface((200, 60), pygame.SRCALPHA)
        hud_surface.fill((0, 0, 0, 128))
        self.screen.blit(hud_surface, (10, 10))
        
        self.screen.blit(speed_text, (20, 20))
        self.screen.blit(alt_text, (20, 50))
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        """Main game loop."""
        try:
            # Try to connect to the joystick
            ser = self.find_joystick()
            
            if ser:
                print("Joystick connected!")
                
                while self.running:
                    self.handle_events()
                    
                    # Read joystick data
                    if ser.in_waiting:
                        try:
                            line = ser.readline().decode('utf-8').strip()
                            if 'X:' in line and 'Y:' in line:
                                parts = line.replace('X:', ',').replace('Y:', ',').split(',')
                                if len(parts) >= 3:
                                    self.joystick_x = int(parts[1])
                                    self.joystick_y = int(parts[2])
                        except:
                            pass
                    
                    self.update()
                    self.draw()
                    self.clock.tick(FPS)
                
                ser.close()
            
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            pygame.quit()
            sys.exit()
    
    def find_joystick(self):
        """Find and connect to the joystick."""
        ports = list(serial.tools.list_ports.comports())
        
        for port in ports:
            try:
                print(f"Trying {port.device}...")
                ser = serial.Serial(port.device, BAUD_RATE, timeout=0.1)
                time.sleep(0.5)  # Give it time to initialize
                
                # Test for valid data
                for _ in range(5):
                    if ser.in_waiting:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if 'X:' in line and 'Y:' in line:
                            print(f"Found joystick on {port.device}")
                            return ser
                    time.sleep(0.1)
                
                ser.close()
                
            except Exception as e:
                print(f"Error with {port.device}: {e}")
                continue
        
        print("No joystick found. Using keyboard controls (arrow keys).")
        return None

if __name__ == "__main__":
    game = FlightSimulator()
    game.run()

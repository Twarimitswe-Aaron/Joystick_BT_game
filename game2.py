import serial
import serial.tools.list_ports
import time
import pygame
import math

BAUD = 38400  # for HC-05 Bluetooth

# List all COM ports
ports = [p.device for p in serial.tools.list_ports.comports()]
print("Available ports:", ports)

found = None
ser = None

for port in ports:
    try:
        ser_temp = serial.Serial(port, BAUD, timeout=1)
        print(f"Listening on {port}...")
        time.sleep(2)  # allow device to start sending

        # Read multiple lines to increase chances of finding valid data
        for _ in range(10):  # Try reading up to 10 lines
            data = ser_temp.readline().decode(errors='ignore').strip()
            if data:
                print(f"Raw data received: '{data}'")  # Debug output
                try:
                    # Handle both formats: with timestamp and without
                    if "->" in data:
                        # Format: "08:59:30.001 -> X:448,Y:461"
                        data_part = data.split("-> ")[1]
                    else:
                        # Format: "X:448,Y:461"
                        data_part = data
                    
                    # Parse X and Y values (comma separated)
                    if "X:" in data_part and "Y:" in data_part:
                        x_str = data_part.split("X:")[1].split(",")[0]
                        y_str = data_part.split("Y:")[1]
                        
                        x = int(x_str)
                        y = int(y_str)
                        
                        print(f"\n✅ Data found on {port}: X={x}, Y={y}\n")
                        found = port
                        ser = ser_temp  # Keep this serial connection open
                        break
                except Exception as e:
                    print(f"Parsing error: {e}")
                    continue
        
        if found:
            break
        else:
            ser_temp.close()

    except Exception as e:
        print(f"Error on port {port}: {e}")
        # Ignore "semaphore timeout" and similar errors
        pass

if not found:
    print("\n❌ No active COM port produced data in the expected format.")
    print("Please check:")
    print("1. Bluetooth module is powered on")
    print("2. Correct BAUD rate (38400)")
    print("3. Device is actually sending data")
    print("4. No other program is using the serial port")
    exit()

# Set timeout to 0 for non-blocking reads
ser.timeout = 0

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("3D Airplane Control")
clock = pygame.time.Clock()

# Initial values (adjust center based on your device's neutral position)
center_x = 448  # Neutral X from sample data
center_y = 461  # Neutral Y from sample data
x = center_x
y = center_y

# Sensitivity factors (adjust as needed)
roll_max_deg = 45
pitch_max_deg = 30

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Read all available serial data and update to the latest X/Y
    data_buffer = ""
    while True:
        try:
            data = ser.readline().decode(errors='ignore').strip()
            if not data:
                break
            
            print(f"Real-time data: {data}")  # Debug output
            
            try:
                # Handle both formats: with timestamp and without
                if "->" in data:
                    data_part = data.split("-> ")[1]
                else:
                    data_part = data
                
                # Parse X and Y values (comma separated)
                if "X:" in data_part and "Y:" in data_part:
                    x_str = data_part.split("X:")[1].split(",")[0]
                    y_str = data_part.split("Y:")[1]
                    
                    x = int(x_str)
                    y = int(y_str)
                    
            except Exception as e:
                print(f"Real-time parsing error: {e}")
                pass  # Ignore parsing errors
                
        except Exception as e:
            print(f"Serial read error: {e}")
            break

    # Compute roll and pitch angles
    roll = ((x - center_x) / (1023 / 2)) * roll_max_deg  # Normalize to -45 to +45 degrees
    pitch = ((y - center_y) / (1023 / 2)) * pitch_max_deg  # Normalize to -30 to +30 degrees

    # Draw the scene (simulating 3D view with horizon tilt for roll and shift for pitch)
    screen.fill((135, 206, 235))  # Sky blue

    width = 800
    height = 600
    mid_y = height // 2

    # Pitch offset (moves horizon up/down)
    pitch_offset = -pitch * (height / (2 * pitch_max_deg))  # Scale to screen height

    # Roll in radians for calculations
    roll_rad = math.radians(roll)

    # Calculate horizon y positions for left and right (for tilt)
    horizon_dy = math.sin(roll_rad) * (width / 2)
    horizon_left_y = mid_y + pitch_offset - horizon_dy
    horizon_right_y = mid_y + pitch_offset + horizon_dy

    # Clamp to screen bounds if needed
    horizon_left_y = max(0, min(height, horizon_left_y))
    horizon_right_y = max(0, min(height, horizon_right_y))

    # Draw ground polygon (green)
    ground_points = [
        (0, height),
        (width, height),
        (width, horizon_right_y),
        (0, horizon_left_y)
    ]
    pygame.draw.polygon(screen, (34, 139, 34), ground_points)

    # Draw horizon line
    pygame.draw.line(screen, (0, 0, 0), (0, horizon_left_y), (width, horizon_right_y), 2)

    # Draw fixed airplane indicator (crosshair in center, like a heads-up display)
    pygame.draw.line(screen, (255, 0, 0), (400 - 20, 300), (400 + 20, 300), 3)  # Horizontal
    pygame.draw.line(screen, (255, 0, 0), (400, 300 - 20), (400, 300 + 20), 3)  # Vertical
    
    # Display current values
    font = pygame.font.Font(None, 36)
    text = font.render(f"X: {x}, Y: {y}, Roll: {roll:.1f}°, Pitch: {pitch:.1f}°", True, (0, 0, 0))
    screen.blit(text, (10, 10))

    pygame.display.flip()
    clock.tick(60)

# Cleanup
ser.close()
pygame.quit()
import sys
import time

COMPORT = 'COM3'
BAUDRATE = 115200
TIMEOUT = 30

print("[CAPTURE] About to open COM3 at 115200 baud...")
print("[CAPTURE] Please press RESET on board NOW.")
print("[CAPTURE] If SW4 is set to U4, you should see data.")

try:
    import serial
    port = serial.Serial(COMPORT, BAUDRATE, timeout=1)
except Exception as e:
    print(f"[ERROR] pyserial failed: {e}")
    sys.exit(1)

log_file = open('com3_capture.log', 'w', encoding='utf-8')
start = time.time()
total_bytes = 0

while time.time() - start < TIMEOUT:
    data = port.read(1)
    if data:
        total_bytes += len(data)
        try:
            char = data.decode('utf-8')
            sys.stdout.write(char)
            sys.stdout.flush()
            log_file.write(char)
        except UnicodeDecodeError:
            hex_str = data.hex()
            sys.stdout.write(f"<0x{hex_str}>")
            sys.stdout.flush()
            log_file.write(f"<0x{hex_str}>")
        # Reset the 30s timeout on activity
        start = time.time()
    else:
        time.sleep(0.01)

port.close()
log_file.close()

print()
print(f"[CAPTURE] Closed. Total bytes received: {total_bytes}")
if total_bytes == 0:
    print("[CAPTURE] No data received.")
    print("  -> Check that SW4 is set to U4 (not SE)")
    print("  -> Application may not print to UART")
    print("  -> Try power-cycling the board")

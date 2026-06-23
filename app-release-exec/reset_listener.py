import serial
import sys
import time

print("Listening on COM3 at 57600 baud...")
print("Please press the RESET button on your Alif board now.")
print("If the bootloader wakes up, we will see raw bytes.")
print("Press Ctrl-C to stop.")
print("-" * 50)

try:
    port = serial.Serial('COM3', baudrate=57600, timeout=1)
    start = time.time()
    while time.time() - start < 30:
        data = port.read(1)
        if data:
            print(f"BYTE: {data.hex()} ({data})")
            # Read any additional bytes available
            while port.in_waiting:
                extra = port.read(port.in_waiting)
                for b in extra:
                    print(f"BYTE: {b:02x} ({bytes([b])})")
    print("-" * 50)
    print("No response detected within 30 seconds.")
    print("Possible causes:")
    print("  - Board not powered")
    print("  - Wrong USB port (must be PRG USB)")
    print("  - Board needs power cycle (unplug/replug USB)")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

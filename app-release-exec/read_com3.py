#!/usr/bin/env python3
"""Listen on COM3 for Alif E8 application boot messages."""

# Import serial API from the Python distribution
import sys
import time

# We use the bundled Python, so let's try its serial capabilities
# If pyserial is not available, we use the .NET SerialPort via PowerShell

COMPORT = 'COM3'
BAUDRATE = 115200  # Most embedded apps use 115200
ALTERNATE_BAUDS = [57600, 9600]

def listen_via_system_io():
    """Use .NET System.IO.Ports.SerialPort which is always available on Windows."""
    import clr
    clr.AddReference('System')
    from System.IO.Ports import SerialPort
    from System import TimeoutException

    for baud in [BAUDRATE] + ALTERNATE_BAUDS:
        try:
            port = SerialPort(COMPORT, baud)
            port.ReadTimeout = 1000
            port.WriteTimeout = 1000
            port.Open()
            print(f"[INFO] Opened {COMPORT} at {baud} baud")
            print("[INFO] Waiting for data... (press RESET on board now)")
            print("-" * 50)

            start = time.time()
            total_data = []
            while time.time() - start < 45:
                try:
                    data = port.ReadExisting()
                    if data:
                        sys.stdout.write(str(data))
                        sys.stdout.flush()
                        total_data.append(str(data))
                        start = time.time()  # Reset timeout on activity
                except TimeoutException:
                    pass
                time.sleep(0.05)

            port.Close()
            print()
            print("-" * 50)
            print("[INFO] Listener closed after 45 seconds of inactivity.")
            if not total_data:
                print("[WARNING] No data received.")
                print("  Possible causes:")
                print("    - SW4 is not set to U4")
                print("    - Application does not print to UART")
                print("    - Wrong baud rate (tried: " + str([BAUDRATE] + ALTERNATE_BAUDS) + ")")
            return
        except Exception as e:
            print(f"[WARN] Failed at {baud} baud: {e}")
            continue

try:
    # Try pythonnet first (System.IO.Ports)
    import clr
    listen_via_system_io()
except ImportError:
    # Fallback: try PowerShell via subprocess
    print("[WARN] pythonnet (clr) not available, trying fallback...")
    # But we are in a Python script; the caller should use PowerShell directly
    sys.exit(1)

import subprocess
import sys
import time

cmd = ['C:\\Users\\mason\\alif\\alif_ml-embedded-evaluation-kit\\tools\\app-release-exec\\maintenance.exe']
proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd='C:\\Users\\mason\\alif\\alif_ml-embedded-evaluation-kit\\tools\\app-release-exec'
)

def wait_for(target, timeout=15):
    buf = ''
    start = time.time()
    while time.time() - start < timeout:
        ch = proc.stdout.read(1)
        if not ch:
            return False, buf
        sys.stdout.write(ch)
        sys.stdout.flush()
        buf += ch
        if target in buf:
            return True, buf
    return False, buf

# Step 1: Wait for main menu prompt
ok, _ = wait_for("Select an option (Enter to exit):", timeout=10)
if not ok:
    print("\n[ERROR] Did not see main menu. Check COM3 connection.", file=sys.stderr)
    proc.kill()
    sys.exit(1)

# Enter Device Control
proc.stdin.write("1\r\n")
proc.stdin.flush()

# Step 2: Wait for sub-menu prompt
ok, _ = wait_for("Select an option (Enter to return):", timeout=10)
if not ok:
    print("\n[ERROR] Did not see Device Control sub-menu.", file=sys.stderr)
    proc.kill()
    sys.exit(1)

# Enter Hard maintenance mode
proc.stdin.write("1\r\n")
proc.stdin.flush()

# Step 3: Wait for the exact reset prompt
ok, _ = wait_for("[RESET Platform]", timeout=15)
if not ok:
    print("\n[ERROR] Did not reach RESET prompt. Board may not be responding.", file=sys.stderr)
    proc.kill()
    sys.exit(1)

# Prompt user
print("\n" + "="*60, file=sys.stderr)
print(">>> PLEASE PRESS THE RESET BUTTON ON YOUR ALIF BOARD NOW <<<", file=sys.stderr)
print("="*60 + "\n", file=sys.stderr)
print("Listening for target response...", file=sys.stderr)

# Step 4: Listen for connection result (up to 25 s after reset)
ok, buf = wait_for("Hard maintenance mode", timeout=25)
if ok:
    print(">>> SUCCESS: Board entered Hard Maintenance Mode! <<<")
else:
    print(">>> Timed out waiting for maintenance mode confirmation. <<<")

proc.stdin.close()
proc.wait()

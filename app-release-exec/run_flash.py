import subprocess
import sys
import time
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
exe = os.path.join(script_dir, 'app-write-mram.exe')

# Run app-write-mram.exe with COM3 specified directly and padding enabled.
# Give it a ~12 s grace period for a non-responsive board, then kill.
proc = subprocess.Popen(
    [exe, '-c', 'COM3', '-p', '-d'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=script_dir
)

try:
    output, _ = proc.communicate(timeout=12)
except subprocess.TimeoutExpired:
    proc.kill()
    output, _ = proc.communicate()

print(output)
sys.stdout.flush()

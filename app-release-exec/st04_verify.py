import subprocess
import os
import sys
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
exe = os.path.join(script_dir, 'app-write-mram.exe')

# Run app-write-mram with COM3 specified; kill after 15 s so we can capture
# any early output (e.g. COM3 open Serial port success / Target did not respond).
proc = subprocess.Popen(
    [exe, '-c', 'COM3', '-p'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=script_dir,
    encoding='utf-8',
    errors='replace'
)

try:
    output, _ = proc.communicate(timeout=15)
except subprocess.TimeoutExpired:
    proc.kill()
    output, _ = proc.communicate()

print(output)
sys.stdout.flush()

# Also append to a persistent log
log_path = os.path.join(script_dir, 'st04_flash_attempt.log')
with open(log_path, 'w', encoding='utf-8', errors='replace') as f:
    f.write(output)

# Simple pattern check
patterns = ['Done!', 'COM3 open Serial port success', 'Target did not respond']
found = {p: p in output for p in patterns}
for p, ok in found.items():
    print(f"[VERIFY] {'PASS' if ok else 'MISSING'} -> '{p}'")

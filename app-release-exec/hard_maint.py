import subprocess
import sys

# Run maintenance.exe from its own directory so bin/ and utils/ are found
cmd = ['maintenance.exe']
proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd='C:\\Users\\mason\\alif\\alif_ml-embedded-evaluation-kit\\tools\\app-release-exec'
)

# Sequence: 1 (Device Control) -> 1 (Hard maintenance mode)
proc.stdin.write('1\r\n')
proc.stdin.flush()
proc.stdin.write('1\r\n')
proc.stdin.flush()

try:
    output, _ = proc.communicate(timeout=30)
except subprocess.TimeoutExpired:
    proc.kill()
    output, _ = proc.communicate()

print(output)
sys.stdout.flush()

import subprocess
import sys

cmd = ['app-write-mram.exe', '-d', '-p']

proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Feed COM3 to the interactive prompt
proc.stdin.write('COM3\r\n')
proc.stdin.flush()

try:
    output, _ = proc.communicate(timeout=30)
except subprocess.TimeoutExpired:
    proc.kill()
    output, _ = proc.communicate()

print(output)
sys.stdout.flush()

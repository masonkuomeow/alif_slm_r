#!/usr/bin/env python3
"""Flash Alif E8 with filtered output to avoid console buffer overflow."""
import subprocess
import sys
import threading
import time

TOOL_DIR = r'C:\Users\mason\alif\alif_ml-embedded-evaluation-kit\tools\app-release-exec'

print("="*60)
print("Flashing Alif E8 via COM3 in Maintenance Mode")
print("Please ensure board is in Hard Maintenance Mode")
print("="*60)
print()

# Start flash process
flash = subprocess.Popen(
    ['app-write-mram.exe', '-c', 'COM3', '-d', '-p'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=TOOL_DIR
)

# Send COM3 response
flash.stdin.write('COM3\r\n')
flash.stdin.flush()

last_progress = ""
important_lines = []
critical_keywords = ['ERROR', 'Done', 'Success', 'Complete', 'Failed', 'Maintenance Mode', 'Authenticate', 'Download Image', 'COM3 open']

def read_output():
    global last_progress
    for line in flash.stdout:
        line_stripped = line.rstrip('\n')
        if not line_stripped:
            continue
        # Check if this is a progress bar line (contains percentage)
        if 'bytes' in line_stripped and ('%' in line_stripped or '[' in line_stripped):
            last_progress = line_stripped
        elif any(kw in line_stripped for kw in critical_keywords):
            print(line_stripped, flush=True)
            important_lines.append(line_stripped)
        else:
            # Other lines - print if short
            if len(line_stripped) < 200:
                print(line_stripped, flush=True)
                important_lines.append(line_stripped)
            else:
                last_progress = line_stripped[:100]

reader = threading.Thread(target=read_output)
reader.daemon = True
reader.start()

try:
    flash.wait(timeout=3600)
except subprocess.TimeoutExpired:
    flash.kill()
    flash.wait()

reader.join(timeout=2)

# Print final progress summary
print("="*60, flush=True)
if last_progress:
    print(f"Last progress: {last_progress}", flush=True)

# Check result
output_text = '\n'.join(important_lines)
if 'Done' in output_text or 'successfully' in output_text.lower():
    print(">>> FLASH COMPLETED SUCCESSFULLY <<<")
elif 'ERROR' in output_text or 'Failed' in output_text:
    print(">>> FLASH FAILED - see errors above <<<")
else:
    print(">>> Flash process exited. Check output above for final status. <<<")

print("="*60, flush=True)

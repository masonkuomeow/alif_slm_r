#!/usr/bin/env python3
"""Flash Alif E8 using maintenance mode + app-write-mram with proper sequencing."""
import subprocess
import sys
import time
import os

TOOL_DIR = r'C:\Users\mason\alif\alif_ml-embedded-evaluation-kit\tools\app-release-exec'

# Step 1: Enter soft maintenance mode first
print("="*60)
print("STEP 1: Entering SOFT Maintenance Mode")
print("="*60)
maint = subprocess.Popen(
    ['maintenance.exe', '-c', 'COM3'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=TOOL_DIR
)

# Send Device Control (1), Soft Maintenance Mode (2)
maint.stdin.write('1\n')
maint.stdin.flush()
time.sleep(1)
maint.stdin.write('2\n')  # Soft maintenance mode
maint.stdin.flush()

# Wait a bit for it to stabilize
output = ""
try:
    out, _ = maint.communicate(timeout=8)
    output = out
    print(out)
except subprocess.TimeoutExpired:
    maint.kill()
    out, _ = maint.communicate()
    output = out
    print(out)

if "Soft maintenance mode" in output:
    print("SOFT MAINTENANCE MODE ACTIVE!")
else:
    print("WARNING: Soft maintenance mode may not have activated.")
    print("This might still work if SW4 is set to SE.")

# Step 2: Flash
print()
print("="*60)
print("STEP 2: Flashing MRAM")
print("="*60)

flash = subprocess.Popen(
    ['app-write-mram.exe', '-c', 'COM3', '-d', '-p'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=TOOL_DIR
)

# The -c COM3 should specify the port, but the tool may still prompt.
# Send COM3 just in case.
flash.stdin.write('COM3\n')
flash.stdin.flush()

try:
    out, _ = flash.communicate(timeout=120)
    print(out)
except subprocess.TimeoutExpired:
    print("Flash timed out after 120 seconds. Killing...")
    flash.kill()
    out, _ = flash.communicate()
    print(out)

print("="*60)
print("Done.")
print("="*60)

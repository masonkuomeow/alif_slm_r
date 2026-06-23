#!/usr/bin/env python3
"""
Deploy firmware to Alif Ensemble E8 via SETOOLS (Alif Security Toolkit).
"""
import subprocess
import sys
import os
import time
import shutil
import argparse
import threading

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.join(SCRIPT_DIR, 'app-release-exec')
MAINT_EXE = os.path.join(TOOL_DIR, 'maintenance.exe')
FLASH_EXE = os.path.join(TOOL_DIR, 'app-write-mram.exe')
TOC_EXE = os.path.join(TOOL_DIR, 'app-gen-toc.exe')
TARGET_BIN = os.path.join(TOOL_DIR, 'build', 'images', 'alif-img.bin')


def log(msg):
    print(msg, flush=True)


def cleanup_processes():
    for exe_name in ['app-write-mram.exe', 'maintenance.exe']:
        try:
            subprocess.run(
                ['taskkill', '/f', '/im', exe_name],
                capture_output=True, timeout=10
            )
        except Exception:
            pass
    time.sleep(0.5)


def check_com_port(comport):
    try:
        r = subprocess.run(
            f'mode {comport}',
            capture_output=True, text=True, timeout=5, shell=True,
            encoding='utf-8', errors='replace'
        )
        if r.returncode == 0 or comport.upper() in r.stdout.upper():
            log(f"[INIT] {comport} found.")
            return True
    except Exception:
        pass
    log(f"[INIT] ERROR: {comport} not found. Is the board connected?")
    return False


def prepare_image(binary_path):
    abs_binary = os.path.abspath(binary_path)
    if not os.path.exists(abs_binary):
        alt = os.path.join(SCRIPT_DIR, binary_path)
        if os.path.exists(alt):
            abs_binary = os.path.abspath(alt)
        else:
            log(f"[PREP] ERROR: Binary not found: {abs_binary}")
            return False

    size = os.path.getsize(abs_binary)
    log(f"[PREP] Source: {abs_binary} ({size} bytes)")

    shutil.copy2(abs_binary, TARGET_BIN)
    log(f"[PREP] Copied to: {TARGET_BIN}")

    log("[PREP] Generating ATOC ...")
    proc = subprocess.run(
        [TOC_EXE, '-f', 'alif-img.json'],
        capture_output=True, text=True, cwd=TOOL_DIR,
        encoding='utf-8', errors='replace', timeout=120
    )
    log(proc.stdout.rstrip())
    if proc.returncode != 0 or 'Done!' not in proc.stdout:
        log("[PREP] ERROR: ATOC generation failed.")
        return False

    log("[PREP] ATOC OK.")
    return True


def enter_maintenance(comport):
    log(f"[MAINT] Starting maintenance.exe on {comport} ...")
    proc = subprocess.Popen(
        [MAINT_EXE, '-c', comport],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, cwd=TOOL_DIR,
        encoding='utf-8', errors='replace'
    )

    buf = ''
    found = [False]

    def read_until(target, timeout_s):
        nonlocal buf
        start = time.time()
        while time.time() - start < timeout_s:
            if proc.poll() is not None:
                return False
            ch = proc.stdout.read(1)
            if ch:
                buf += ch
                sys.stdout.write(ch)
                sys.stdout.flush()
                if target in buf:
                    return True
            else:
                time.sleep(0.01)
        return False

    # Step 1: main menu
    if not read_until("Select an option", timeout_s=15):
        log("\n[MAINT] ERROR: Board not responding on COM3.")
        proc.kill(); proc.wait()
        return False

    time.sleep(0.5)
    proc.stdin.write('1\n'); proc.stdin.flush()

    # Step 2: sub-menu
    buf = ''
    if not read_until("Select an option", timeout_s=10):
        log("\n[MAINT] ERROR: Sub-menu not seen.")
        proc.kill(); proc.wait()
        return False

    time.sleep(0.5)
    proc.stdin.write('2\n'); proc.stdin.flush()

    # Step 3: confirmation
    buf = ''
    log("\n[MAINT] Waiting for Soft Maintenance Mode ...")
    if read_until("Soft maintenance mode", timeout_s=15):
        log("\n[MAINT] Soft Maintenance Mode ACTIVE.")
        proc.stdin.close(); proc.wait()
        return True

    log("\n[MAINT] WARNING: Could not confirm maintenance mode.")
    proc.kill(); proc.wait()
    return False


def flash_binary(comport, timeout_s=300):
    log(f"[FLASH] Starting app-write-mram.exe on {comport} ...")

    log_file = os.path.join(TOOL_DIR, 'flash_output.log')
    with open(log_file, 'w', encoding='utf-8', errors='replace') as flog:
        proc = subprocess.Popen(
            [FLASH_EXE, '-c', comport, '-p'],
            stdout=flog, stderr=subprocess.STDOUT,
            cwd=TOOL_DIR
        )

        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
            log("[FLASH] Timed out!")
            return False

    # Read the log file to check result
    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as flog:
            output = flog.read()
    except Exception:
        output = ''

    # Print only key lines (not the thousands of progress lines)
    for line in output.splitlines():
        stripped = line.strip()
        if any(k in stripped for k in ['Done!', 'FAILED', 'ERROR', 'Target did not respond',
                                        'Detected Device', 'Maintenance Mode', 'Burning:',
                                        'baud rate', 'Serial port']):
            log(stripped)

    if 'Done!' in output:
        log("[FLASH] SUCCESS!")
        return True
    elif proc.returncode == 0:
        log("[FLASH] Completed (rc=0).")
        return True
    else:
        log(f"[FLASH] FAILED (rc={proc.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(description='Deploy firmware via Alif SETOOLS')
    parser.add_argument('binary', help='Path to the binary file to flash')
    parser.add_argument('--com', default='COM3', help='COM port (default: COM3)')
    parser.add_argument('--skip-maint', action='store_true')
    parser.add_argument('--maint-only', action='store_true')
    args = parser.parse_args()

    log("=" * 60)
    log("  Alif SETOOLS Deploy")
    log("=" * 60)

    # Cleanup
    log("[INIT] Cleaning up stale processes ...")
    cleanup_processes()

    # Check port
    if not check_com_port(args.com):
        log("=" * 60)
        log("  DEPLOY FAILED")
        log("=" * 60)
        return 1

    # Prepare image
    if not args.maint_only:
        if not prepare_image(args.binary):
            return 1

    # Maintenance mode
    if not args.skip_maint:
        if not enter_maintenance(args.com):
            log("[WARN] Soft maintenance failed.")
            log("[WARN] Please put board into Hard Maintenance Mode using SW2:")
            log("[WARN]   1. Set SW2 to ISP position")
            log("[WARN]   2. Press RESET")
            log("[WARN]   3. Set SW2 back to normal position")
            log("[WARN] Then re-run with --skip-maint")
            return 1
        time.sleep(1)
    else:
        log("[MAINT] Skipped (--skip-maint)")

    if args.maint_only:
        log("[DONE] Maintenance entry complete.")
        return 0

    # Flash
    ok = flash_binary(args.com)

    log("=" * 60)
    log("  DEPLOY SUCCESSFUL" if ok else "  DEPLOY FAILED")
    log("=" * 60)

    cleanup_processes()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

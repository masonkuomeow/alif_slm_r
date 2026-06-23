# Alif Ensemble E8 -- Firmware Development Reference

Based on [Arm Learning Path: Run image classification on an Alif Ensemble E8 DevKit](https://learn.arm.com/learning-paths/embedded-and-microcontrollers/alif-image-classification/)

---

## Overview

Deploy neural network models (e.g. MobileNetV2) to the Alif Ensemble E8 DevKit
using ExecuTorch and the Ethos-U85 NPU. The E8 has two Cortex-M55 cores:

| Core    | Role   | MRAM base    | Config file              |
|---------|--------|--------------|--------------------------|
| M55_HP  | High-Performance | `0x80200000` | `.alif/M55_HP_cfg.json`  |
| M55_HE  | High-Efficiency  | `0x80000000` | `.alif/M55_HE_cfg.json`  |

---

## Prerequisites

### Hardware
- Alif Ensemble E8 DevKit + USB-C cable
- SEGGER J-Link debug probe (included in DevKit)

### Software
- CMSIS-Toolbox >= 2.12 (`cbuild`, `cpackget`)
- Arm GNU Toolchain (arm-none-eabi-gcc >= 13.2)
- CMake >= 3.28, Ninja >= 1.12
- Python 3.12 (bundled at `python/python.exe`)
- pyOCD (for JTAG/SWD flashing)
- Alif Security Toolkit (SETOOLS) at `app-release-exec/`
- SEGGER J-Link software (for RTT viewer and debugging)

### First-time Pack Installation
```bash
cpackget init https://www.keil.com/pack/index.pidx
cpackget add https://github.com/ARM-software/CMSIS_6/releases/download/v6.0.0/ARM.CMSIS.6.0.0.pack
cpackget add https://github.com/alifsemi/alif_ensemble-cmsis-dfp/releases/download/v2.0.4/AlifSemiconductor.Ensemble.2.0.4.pack
```

Packs used (from `alif.csolution.yml`):
- `AlifSemiconductor::Ensemble@2.0.4`
- `ARM::CMSIS@6.0.0`

---

## Board Setup

### USB Connections
The DevKit exposes two USB interfaces over USB-C:
1. **CMSIS-DAP** -- for JTAG/SWD debug (pyOCD, J-Link)
2. **Virtual COM Port (COM3)** -- for SE Tools serial communication and UART output

### SW4 Switch Position
| Position | Function |
|----------|----------|
| **U4**   | UART mode -- COM3 connected to M55_HE/M55_HP UART (for printf output and SE Tools) |
| **SE**   | JTAG/SE mode -- COM3 connected to Secure Enclave |

For SE Tools flashing: **SW4 must be set to U4** (default).
For SEGGER RTT output: SW4 position does not matter (RTT uses JTAG).

---

## Project Structure

```
alif_vscode-template/
  alif.csolution.yml          # Solution file (targets, packs, projects)
  .alif/
    M55_HE_cfg.json           # SE Tools image config for M55_HE
    M55_HP_cfg.json           # SE Tools image config for M55_HP
    JLinkDevices.xml          # J-Link device definitions
  hello/
    hello.cproject.yml        # Project config (stdout via CMSIS-Compiler)
    main.c                    # Hello World application
  hello_rtt/
    hello_rtt.cproject.yml    # Project config (output via SEGGER RTT)
    main.c                    # RTT-based application
  blinky/
    blinky.cproject.yml       # Blinky LED project
  device/ensemble/
    alif-ensemble.clayer.yml  # Shared device layer (startup, peripherals, BSP)
  libs/
    SEGGER_RTT_V796h/         # SEGGER RTT library
    common_app_utils/         # Fault handler and utilities
  out/
    hello/E8-HE/debug/
      hello.elf               # Built ELF
      hello.bin               # Built binary (for flashing)
```

---

## Build

### Command Line
```bash
# Build hello project for E8 M55_HE core (debug)
cbuild alif.csolution.yml --context hello.debug+E8-HE

# Build for E8 M55_HP core
cbuild alif.csolution.yml --context hello.debug+E8-HP

# Build blinky
cbuild alif.csolution.yml --context blinky.debug+E8-HE

# Build hello_rtt (SEGGER RTT output)
cbuild alif.csolution.yml --context hello_rtt.debug+E8-HE
```

Output goes to `out/<project>/<target>/<build-type>/`:
- `<project>.elf`
- `<project>.bin`

### In VS Code
Use the CMSIS extension: Ctrl+Shift+P -> "CMSIS: Build"

---

## Flash / Deploy

### Method 1: pyOCD (via CMSIS-DAP/JTAG)

Requires: SEGGER J-Link or CMSIS-DAP probe connected via USB.

```bash
# Load firmware
pyocd load --probe cmsisdap: --cbuild-run out/hello/debug+E8-HE.cbuild-run.yml

# Erase chip
pyocd erase --probe cmsisdap: --chip --cbuild-run out/hello/debug+E8-HE.cbuild-run.yml
```

In VS Code: Run task "CMSIS Load" or "CMSIS Load+Run".

### Method 2: Alif Security Toolkit (SETOOLS via COM3 serial)

Requires: Board connected via USB-C, COM3 available, SW4 = U4.

The full flow has 3 steps:

#### Step 1 -- Copy binary and generate ATOC
```bash
# Copy built binary to SETOOLS build directory
copy out\hello\E8-HE\debug\hello.bin app-release-exec\build\images\alif-img.bin

# Copy the correct image config (M55_HE or M55_HP)
copy .alif\M55_HE_cfg.json app-release-exec\alif-img.json

# Generate ATOC package (Application Table of Contents)
cd app-release-exec
app-gen-toc.exe -f alif-img.json
```

#### Step 2 -- Enter Maintenance Mode
```bash
# Run maintenance tool
maintenance.exe -c COM3

# In the interactive menu:
#   1 -> Device Control
#   2 -> Soft maintenance mode (no physical reset needed)
# OR:
#   1 -> Hard maintenance mode (requires pressing RESET button on board)
```

#### Step 3 -- Flash
```bash
# From app-release-exec/ directory (CWD matters -- tool needs utils/ subfolder)
app-write-mram.exe -c COM3 -p
```

Flags:
- `-c COM3` -- specify COM port
- `-p` -- pad binary if size not multiple of 16
- `-nr` -- no reset before operation
- `-d` -- COM port discovery (interactive, prompts for port)
- `-b 115200` -- change baud rate

**Important**: Always run SETOOLS from the `app-release-exec/` directory. The
tools are PyInstaller-bundled Python executables that look for `utils/` relative
to CWD.

### Automated Deploy Script

A convenience script `deploy_setools.py` automates the full flow:

```bash
python\python.exe deploy_setools.py alif_vscode-template\out\hello\E8-HE\debug\hello.bin --com COM3
```

Or via the wrapper: `flash.bat`

---

## Memory Layout (M55_HE)

From `linker_gnu_mram.ld`:

| Region | Address        | Size   | Purpose                        |
|--------|----------------|--------|--------------------------------|
| ITCM   | `0x00000000`   | 256 KB | Instruction Tightly Coupled    |
| DTCM   | `0x20000000`   | 256 KB | Data Tightly Coupled (stack, heap, data, bss) |
| SRAM0  | `0x02000000`   | 4 MB   | LCD/camera buffers             |
| SRAM1  | `0x02400000`   | 4 MB   | General purpose                |
| MRAM   | `0x80000000`   | 2 MB   | Code + read-only data (execute-in-place) |

Key sections:
- Stack: 8 KB at top of DTCM
- Heap: 16 KB in DTCM
- App heap: 16 KB in DTCM
- Code: loaded from MRAM to ITCM at boot
- Data: loaded from MRAM to DTCM at boot

---

## Verify Output

### Method 1: UART over COM3 (printf via CMSIS-Compiler)

Project: `hello/` (uses `ARM::CMSIS-Compiler:STDOUT:Custom` + `AlifSemiconductor::Services:Retarget IO:STDOUT`)

```bash
# Read serial output
python\python.exe -m serial.tools.miniterm COM3 115200
```

Expected:
```
Hello World!
```

### Method 2: SEGGER RTT (via JTAG)

Project: `hello_rtt/` (uses SEGGER_RTT library directly)

1. Open SEGGER RTT Viewer
2. Connect to target via J-Link
3. Select "USB" connection, device "AE822FA0E5597LS0_M55_HE"
4. Output appears in Terminal tab 0

Or via VS Code: launch config "Alif Ensemble Debug (Cortex-Debug)" has RTT
enabled automatically (`rttConfig` in launch.json).

---

## Troubleshooting

### "Target did not respond" from SE Tools
- Power-cycle the board (unplug USB, wait 10 seconds, reconnect)
- Ensure SW4 is set to U4
- Check COM3 is not held by a previous process: `taskkill /f /im app-write-mram.exe`

### COM3 locked / PermissionError
Kill stale processes:
```bash
taskkill /f /im app-write-mram.exe
taskkill /f /im maintenance.exe
```

### "Enter port name" prompt from app-write-mram
Do not use `-d` flag together with `-c COM3`. The `-d` flag triggers
interactive COM port discovery which overrides `-c`.

### SETOOLS FileNotFoundError
The tools must be run from the `app-release-exec/` directory as CWD.
They look for `utils/` relative to the current directory.

### Build fails with pack errors
Re-install packs:
```bash
cpackget add ARM.CMSIS.6.0.0.pack
cpackget add AlifSemiconductor.Ensemble.2.0.4.pack
```

---

## CMSIS Project Files Reference

### alif.csolution.yml
- Solution-level: defines targets (E7-HE, E7-HP, E1C-HE, E8-HE, E8-HP),
  build types (debug, release), packs, and compiler (GCC)

### *.cproject.yml
- Project-level: defines source files, output types (elf, bin), components
  (CMSIS-Compiler, BSP, Retarget IO), and layers

### *.clayer.yml
- Layer-level: shared device components (startup, GPIO, USART, Secure Enclave,
  BSP board config)

### SE Tools Image Config (.alif/*_cfg.json)
```json
{
  "DEVICE": {
    "binary": "app-device-config.json",
    "version": "0.5.00",
    "signed": true
  },
  "USER_APP": {
    "binary": "alif-img.bin",
    "mramAddress": "0x80000000",
    "cpu_id": "M55_HE",
    "flags": ["boot"]
  }
}
```

---

## fwauto Config (`.fwauto/config.toml`)

```toml
[build]
type = "command"
command = "cbuild alif.csolution.yml --context hello.debug+E8-HE"

[deploy]
type = "command"
command = "cmd /c C:\\Users\\mason\\alif_slm\\flash.bat"

[log]
type = "serial"
serial_port = "COM3"
baudrate = 115200
```

Use `/build`, `/deploy`, `/log` commands for automated workflows.

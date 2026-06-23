#!/usr/bin/env python3
"""
Flask web server for the stories260K LLM demo on Alif E8 board.

Features:
  - Background thread reads serial output from the board
  - Board state machine: IDLE -> READY -> CLASSIFYING -> DONE -> READY ...
  - SSE /api/stream endpoint streams serial lines to the browser
  - POST /api/prompt sends a prompt string to the board over serial
  - DTR/RTS reset on connect to cleanly restart the board
  - GET / serves the dashboard HTML
  - Demo mode with simulated responses when board is not available
"""

import json
import os
import queue
import random
import re
import threading
import time

import serial
import serial.tools.list_ports
from flask import Flask, Response, jsonify, request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BAUD_RATE = 115200
SERIAL_PORT = None  # e.g. "COM3" -- override here or via env
SERIAL_TIMEOUT = 0.1  # read timeout in seconds
DTR_RESET_DELAY = 0.5  # seconds to hold DTR low during reset
POST_RESET_WAIT = 2.0  # seconds to wait after reset before reading
RECONNECT_INTERVAL = 3.0  # seconds between reconnection attempts
DEMO_MODE = False  # Set True to use simulated board responses

# ---------------------------------------------------------------------------
# Simulated LLM responses for demo mode
# ---------------------------------------------------------------------------
LLM_RESPONSES = {
    "apple": ("a fruit that grows on trees. It is red, green, or yellow and is "
              "often eaten raw or used in pies and juice.", 470, 23.5),
    "banana": ("a long curved fruit with a yellow skin. It is sweet and soft "
               "and is one of the most popular fruits in the world.", 485, 24.2),
    "cat": ("a small furry animal that is often kept as a pet. Cats like to "
            "sleep and play with yarn.", 460, 23.0),
    "dog": ("a friendly animal that is loyal to its owner. Dogs come in many "
            "sizes and like to play fetch.", 472, 23.6),
    "car": ("a vehicle with four wheels that is powered by an engine. People "
            "use cars to travel on roads.", 455, 22.8),
    "airplane": ("a large flying vehicle with wings and engines. Airplanes "
                 "carry passengers through the sky.", 490, 24.5),
    "elephant": ("the largest land animal. Elephants have long trunks and "
                 "big ears and live in Africa and Asia.", 502, 25.1),
    "guitar": ("a musical instrument with six strings. People play guitar "
               "by strumming or picking the strings.", 468, 23.4),
    "mountain": ("a very tall natural landform that rises above the "
                 "surrounding land. Mountains have peaks and slopes.", 495, 24.8),
    "book": ("an object with many pages of text. People read books to "
             "learn new things or enjoy stories.", 448, 22.4),
    "fish": ("an animal that lives in water and breathes through gills. "
             "Fish come in many colors and sizes.", 462, 23.1),
    "rocket": ("a vehicle that travels into space using powerful engines. "
               "Rockets carry satellites and astronauts.", 480, 24.0),
    "bicycle": ("a two-wheeled vehicle powered by pedaling. Bicycles are "
                "used for transportation and exercise.", 475, 23.8),
    "flower": ("the colorful part of a plant. Flowers smell nice and help "
               "plants make seeds.", 440, 22.0),
    "spider": ("a small creature with eight legs. Spiders spin webs to "
               "catch insects for food.", 455, 22.8),
    "clock": ("a device that shows the time. Clocks can be analog with "
              "hands or digital with numbers.", 450, 22.5),
}

DEFAULT_RESPONSE = (
    "a thing that exists in the world. It has interesting properties "
    "and people interact with it in many ways.", 470, 23.5
)


# ---------------------------------------------------------------------------
# Board state machine
# ---------------------------------------------------------------------------
STATE_IDLE = "IDLE"
STATE_READY = "READY"
STATE_CLASSIFYING = "CLASSIFYING"
STATE_DONE = "DONE"


class BoardStateMachine:
    """Tracks the current state of the firmware running on the board."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state = STATE_IDLE
        self.last_output = ""
        self.prompt_history: list = []

    def transition(self, new_state: str):
        with self.lock:
            old = self.state
            self.state = new_state
            print(f"[STATE] {old} -> {new_state}")

    def get_state(self) -> str:
        with self.lock:
            return self.state

    def append_output(self, line: str):
        with self.lock:
            self.last_output += line + "\n"

    def record_prompt(self, prompt: str, output: str):
        with self.lock:
            self.prompt_history.append({"prompt": prompt, "output": output})
            if len(self.prompt_history) > 50:
                self.prompt_history = self.prompt_history[-50:]


# ---------------------------------------------------------------------------
# Serial manager
# ---------------------------------------------------------------------------
class SerialManager:
    """Opens serial port, resets the board, reads lines in background."""

    def __init__(self):
        self.port_name: str = SERIAL_PORT
        self.ser: serial.Serial = None
        self.connected = False
        self.demo_mode = DEMO_MODE
        self.skip_reset = False
        self.machine = BoardStateMachine()
        self._subscribers: list = []
        self._sub_lock = threading.Lock()
        self._thread: threading.Thread = None
        self._running = False

    # -- public API ---------------------------------------------------------

    def start(self):
        self._running = True
        if self.demo_mode:
            self._thread = threading.Thread(target=self._demo_loop, daemon=True)
        else:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self.ser and self.ser.is_open:
            self.ser.close()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=500)
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def send_prompt(self, text: str):
        """Send a prompt string followed by newline to the board."""
        if self.demo_mode:
            self.machine.transition(STATE_CLASSIFYING)
            self.machine.last_output = ""
            threading.Thread(target=self._simulate_inference, args=(text,),
                             daemon=True).start()
            return

        if self.ser and self.ser.is_open:
            self.machine.transition(STATE_CLASSIFYING)
            self.machine.last_output = ""
            payload = (text + "\n").encode("utf-8")
            self.ser.write(payload)
            self.ser.flush()
            print(f"[SERIAL TX] {text!r}")

    # -- demo mode ----------------------------------------------------------

    def _demo_loop(self):
        """Simulate board boot and READY state in demo mode."""
        self.machine.transition(STATE_IDLE)
        self._publish_log("============================================", "sys")
        self._publish_log(" stories260K LLM - Alif E8 Board", "sys")
        self._publish_log(" Object Classification Demo", "sys")
        self._publish_log("============================================", "sys")
        self._publish_log("Model: 260K params, dim=64, 5 layers", "sys")
        self._publish_log("Tokenizer: 512 tokens (custom BPE)", "sys")
        self._publish_log("", "sys")
        self._publish_log("[MAIN] Initializing model...", "sys")
        time.sleep(0.5)
        self._publish_log("[MAIN] Model initialized OK", "sys")
        self._publish_log("[MAIN] Initializing tokenizer...", "sys")
        time.sleep(0.3)
        self._publish_log("[MAIN] Tokenizer initialized OK", "sys")
        self._publish_log("", "sys")
        self._publish_log("============================================", "sys")
        self._publish_log(" Interactive Classification Mode", "sys")
        self._publish_log("============================================", "sys")
        self._publish_log("", "sys")
        self.connected = True
        self.machine.transition(STATE_READY)
        self._publish({"type": "serial", "line": "READY>"})
        self._publish({"type": "state", "state": STATE_READY})

        # Keep alive
        while self._running:
            time.sleep(1)

    def _simulate_inference(self, text: str):
        """Simulate LLM inference in demo mode."""
        key = text.strip().lower()
        resp = LLM_RESPONSES.get(key, DEFAULT_RESPONSE)
        generated_text, total_ms, ms_per_token = resp

        # Add some randomness
        total_ms += random.randint(-30, 30)
        ms_per_token += random.uniform(-1.0, 1.0)

        prompt_fmt = f"A {text} is a"

        self._publish_log(f"Classifying '{text}'...", "sys")
        self._publish_log(f"Output: ", "model", no_newline=True)

        # Simulate token-by-token output
        tokens = generated_text.split()
        partial = ""
        for i, tok in enumerate(tokens):
            partial += tok + " "
            self._publish({"type": "serial", "line": tok + " " if i == 0 else tok + " "})
            self._publish({"type": "state", "state": STATE_CLASSIFYING})
            time.sleep(random.uniform(0.02, 0.06))

        self._publish_log("", "sys")
        self._publish_log(f"({total_ms} ms total, {ms_per_token:.1f} ms/token)", "sys")
        self._publish_log("DONE>", "ok")
        self._publish_log("", "sys")

        self.machine.transition(STATE_DONE)
        self.machine.record_prompt(text, generated_text)
        self._publish({"type": "state", "state": STATE_DONE})

        # Transition back to READY
        time.sleep(0.5)
        self.machine.transition(STATE_READY)
        self._publish({"type": "serial", "line": "READY>"})
        self._publish({"type": "state", "state": STATE_READY})

    def _publish_log(self, text: str, cls: str = "out", no_newline: bool = False):
        """Publish a log line in demo mode."""
        self._publish({"type": "serial", "line": text})
        self.machine.append_output(text)

    # -- internal -----------------------------------------------------------

    def _publish(self, msg: dict):
        with self._sub_lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass

    def _auto_detect_port(self) -> str:
        keywords = ["alif", "cmsis", "dap", "usb serial", "usb-serial",
                     "silicon labs", "cp210", "ch340", "ftdi", "uart",
                     "jlink", "segger"]
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            mfg = (p.manufacturer or "").lower()
            if any(k in desc or k in mfg for k in keywords):
                print(f"[SERIAL] Auto-detected port: {p.device} ({p.description})")
                return p.device
        ports = list(serial.tools.list_ports.comports())
        if ports:
            print(f"[SERIAL] Using first available port: {ports[0].device}")
            return ports[0].device
        return None

    def _open_port(self) -> bool:
        try:
            port = self.port_name or self._auto_detect_port()
            if port is None:
                return False

            self.ser = serial.Serial(
                port=port,
                baudrate=BAUD_RATE,
                timeout=SERIAL_TIMEOUT,
                write_timeout=2,
            )

            if self.skip_reset:
                print("[SERIAL] Skipping DTR/RTS reset (--no-reset)")
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                time.sleep(0.5)
            else:
                # DTR/RTS reset
                print("[SERIAL] Performing DTR/RTS reset ...")
                self.ser.dtr = False
                self.ser.rts = False
                time.sleep(DTR_RESET_DELAY)
                self.ser.dtr = True
                self.ser.rts = True
                time.sleep(DTR_RESET_DELAY)
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                time.sleep(POST_RESET_WAIT)

            self.connected = True
            self.machine.transition(STATE_IDLE)
            print(f"[SERIAL] Connected to {port} @ {BAUD_RATE}")
            return True

        except (serial.SerialException, OSError) as exc:
            print(f"[SERIAL] Failed to open port: {exc}")
            self.connected = False
            return False

    def _close_port(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.connected = False
        self.machine.transition(STATE_IDLE)

    def _run_loop(self):
        """Main background loop: connect, read, reconnect on failure."""
        last_data_time = None
        probe_sent = False

        while self._running:
            if not self.connected:
                if not self._open_port():
                    # Fall back to demo mode if no board detected after 10s
                    if not self.demo_mode:
                        print("[SERIAL] No board detected. Enabling demo mode.")
                        self.demo_mode = True
                        self._demo_loop()
                        return
                    time.sleep(RECONNECT_INTERVAL)
                    continue
                # Reset probe state on new connection
                last_data_time = time.time()
                probe_sent = False

            try:
                raw = self.ser.readline()
                if not raw:
                    # No data received -- check if we should send a probe
                    if last_data_time and not probe_sent:
                        elapsed = time.time() - last_data_time
                        if elapsed > 3.0:
                            # Board silent for 3s after connect -- send
                            # newline to trigger READY>/Enter prompt cycle
                            print("[SERIAL] Board silent, sending probe newline")
                            self.ser.write(b"\r\n")
                            self.ser.flush()
                            probe_sent = True
                    continue

                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue

                last_data_time = time.time()
                self._publish({"type": "serial", "line": line})
                self.machine.append_output(line)

                if "READY>" in line or "Enter prompt" in line:
                    self.machine.transition(STATE_READY)
                    self._publish({"type": "state", "state": STATE_READY})
                elif "DONE>" in line:
                    self.machine.transition(STATE_DONE)
                    self.machine.record_prompt("", self.machine.last_output)
                    self._publish({"type": "state", "state": STATE_DONE})

            except (serial.SerialException, OSError) as exc:
                print(f"[SERIAL] Connection lost: {exc}")
                self._close_port()
                time.sleep(RECONNECT_INTERVAL)
            except Exception as exc:
                print(f"[SERIAL] Unexpected error: {exc}")
                time.sleep(1)


# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
app = Flask(__name__)
manager = SerialManager()


@app.route("/")
def index():
    """Serve the dashboard HTML page."""
    standalone = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "web_demo.html")
    if os.path.isfile(standalone):
        with open(standalone, encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html"}
    return DASHBOARD_HTML, 200, {"Content-Type": "text/html"}


@app.route("/api/stream")
def stream():
    """SSE endpoint: streams serial lines and state changes to the client."""

    def event_stream():
        q = manager.subscribe()
        try:
            state = manager.machine.get_state()
            yield f"event: state\ndata: {json.dumps({'state': state, 'demo': manager.demo_mode})}\n\n"

            while True:
                try:
                    msg = q.get(timeout=30)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue

                if msg["type"] == "serial":
                    yield f"event: serial\ndata: {json.dumps({'line': msg['line']})}\n\n"
                elif msg["type"] == "state":
                    yield f"event: state\ndata: {json.dumps({'state': msg['state'], 'demo': manager.demo_mode})}\n\n"
        finally:
            manager.unsubscribe(q)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/status")
def status():
    """Return current board state and recent output."""
    return jsonify({
        "state": manager.machine.get_state(),
        "connected": manager.connected,
        "demo_mode": manager.demo_mode,
        "last_output": manager.machine.last_output,
        "history": manager.machine.prompt_history[-10:],
    })


@app.route("/api/prompt", methods=["POST"])
def prompt():
    """Accept a prompt and forward it to the board over serial."""
    data = request.get_json(silent=True) or {}
    text = (data.get("prompt") or "").strip()
    if not text:
        return jsonify({"error": "No prompt provided"}), 400

    state = manager.machine.get_state()
    if state != STATE_READY:
        return jsonify({"error": f"Board not ready (state={state})"}), 409

    manager.send_prompt(text)
    return jsonify({"ok": True, "prompt": text})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Re-trigger DTR/RTS reset and re-open the serial port."""
    manager._close_port()
    time.sleep(0.5)
    if manager.demo_mode:
        manager.machine.transition(STATE_IDLE)
        time.sleep(1)
        manager.machine.transition(STATE_READY)
        return jsonify({"ok": True, "message": "Board reset (demo mode)"})
    if manager._open_port():
        return jsonify({"ok": True, "message": "Board reset"})
    return jsonify({"error": "Could not reconnect after reset"}), 500


# ---------------------------------------------------------------------------
# Dashboard HTML (inline fallback)
# ---------------------------------------------------------------------------
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html><head><title>stories260K Demo</title></head>
<body><h1>stories260K LLM Demo</h1>
<p>Please use web_demo.html for the full dashboard.</p>
</body></html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="stories260K LLM Demo Web Server")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("PORT", 5000)))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--serial-port",
                        default=os.environ.get("SERIAL_PORT"))
    parser.add_argument("--demo", action="store_true",
                        help="Force demo mode with simulated board responses")
    parser.add_argument("--no-reset", action="store_true",
                        help="Skip DTR/RTS reset on connect")
    args = parser.parse_args()

    if args.serial_port:
        manager.port_name = args.serial_port

    if args.demo:
        manager.demo_mode = True

    if args.no_reset:
        manager.skip_reset = True

    print(f"[SERVER] Starting on http://{args.host}:{args.port}")
    if manager.demo_mode:
        print("[SERVER] Running in DEMO mode (simulated board responses)")
    else:
        print("[SERVER] Running in LIVE mode (serial connection to board)")

    manager.start()
    app.run(host=args.host, port=args.port, threaded=True)

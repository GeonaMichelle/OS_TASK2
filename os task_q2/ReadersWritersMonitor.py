"""
Readers-Writers Problem using a MONITOR (writer preference).

A monitor = one lock + condition variables + the shared data it protects.
Python has no built-in monitor keyword, so the class below is the monitor:
  - self.lock       : only one thread can be inside a monitor method at a time
  - self.can_read   : condition variable where readers wait
  - self.can_write  : condition variable where writers wait

Run:  python ReadersWritersMonitor.py
Creates readers_writers_monitor.html (an animated replay of this run)
in the same folder as this script.
"""

import threading
import time
import random
import html
import json
import os
import webbrowser
from pathlib import Path
from datetime import datetime

AUTO_OPEN_HTML = True             # open the generated HTML page in the browser automatically

# ------------------------------------------------------------------
# Settings (change these during the viva and run again)
# ------------------------------------------------------------------
NUM_READERS = 5
NUM_WRITERS = 2
ROUNDS = 3                        # how many times each thread repeats its work

# ------------------------------------------------------------------
# Shared resource (protected by the monitor below)
# ------------------------------------------------------------------
shared_value = 0                  # every write adds 1
last_written = None               # value of the last successful write
last_writer = "-"

# ------------------------------------------------------------------
# Execution log and independent rule checking (own lock)
# ------------------------------------------------------------------
log_lock = threading.Lock()
events = []                       # every real event is stored here (used for the HTML)
log_readers = 0                   # readers inside, counted from the events themselves
log_writers = 0                   # writers inside, counted from the events themselves
max_readers = 0                   # most readers inside at the same time
max_writers = 0                   # most writers inside at the same time (must stay <= 1)
overlap_count = 0                 # times a reader and a writer were inside together
negative_count = 0                # times a counter went below zero
reads_done = 0
writes_done = 0
start_time = time.time()


def record(who, state, note=""):
    """Log one event at the moment it happens. state is one of:
    waiting, reading, writing, finished, idle.
    It is always called while the monitor lock is held, so the monitor
    state saved in the event is exact."""
    global log_readers, log_writers, max_readers, max_writers
    global overlap_count, negative_count, reads_done, writes_done
    with log_lock:
        is_reader = who.startswith("R")
        if state == "reading":
            log_readers += 1
        elif state == "writing":
            log_writers += 1
        elif state == "finished":
            if is_reader:
                log_readers -= 1
                reads_done += 1
            else:
                log_writers -= 1
                writes_done += 1

        # ---- rule checks done on every event ----
        max_readers = max(max_readers, log_readers)
        max_writers = max(max_writers, log_writers)
        if log_writers > 0 and log_readers > 0:
            overlap_count += 1
        if log_readers < 0 or log_writers < 0:
            negative_count += 1

        ms = int(round((time.time() - start_time) * 1000))
        events.append({"n": len(events) + 1, "t": ms, "who": who, "state": state,
                       "ar": monitor.active_readers, "rl": list(monitor.reading_now),
                       "wa": monitor.writer_name, "ww": monitor.waiting_writers,
                       "hb": list(monitor.held_back), "value": shared_value,
                       "last_writer": last_writer, "note": note})
        print(f"[{ms:5d} ms] {who:3} {state:9} {note:40} "
              f"active_readers={monitor.active_readers} writer={monitor.writer_name} "
              f"waiting_writers={monitor.waiting_writers}")


# ------------------------------------------------------------------
# The monitor
# ------------------------------------------------------------------
class ReadersWriterMonitor:
    def __init__(self):
        self.lock = threading.Lock()
        self.can_read = threading.Condition(self.lock)    # readers wait here
        self.can_write = threading.Condition(self.lock)   # writers wait here
        self.active_readers = 0          # readers currently reading
        self.reading_now = []            # names of those readers (for the HTML)
        self.writer_active = False       # True while a writer is writing
        self.writer_name = "no"
        self.waiting_writers = 0         # writers waiting for their turn
        self.held_back = []              # readers made to wait because of writers

    # ---------------- reader side ----------------
    def start_read(self, name):
        with self.lock:
            # Writer preference: a new reader must wait if a writer is writing
            # OR if any writer is already waiting.
            must_wait = self.writer_active or self.waiting_writers > 0
            if must_wait:
                self.held_back.append(name)
            record(name, "waiting", "held back: writer active or waiting" if must_wait else "wants to read")
            while self.writer_active or self.waiting_writers > 0:
                self.can_read.wait()                      # releases the lock while sleeping
            if name in self.held_back:
                self.held_back.remove(name)
            self.active_readers += 1
            self.reading_now.append(name)
            record(name, "reading", f"reads value {shared_value}")

    def end_read(self, name):
        with self.lock:
            self.active_readers -= 1
            self.reading_now.remove(name)
            record(name, "finished", "finished reading")
            if self.active_readers == 0:
                self.can_write.notify()                   # last reader wakes one writer
            record(name, "idle", "leaves the monitor")

    # ---------------- writer side ----------------
    def start_write(self, name):
        with self.lock:
            self.waiting_writers += 1
            record(name, "waiting", "wants to write")
            while self.writer_active or self.active_readers > 0:
                self.can_write.wait()
            self.waiting_writers -= 1
            self.writer_active = True
            self.writer_name = name
            record(name, "writing", "has exclusive access")

    def end_write(self, name):
        with self.lock:
            self.writer_active = False
            self.writer_name = "no"
            record(name, "finished", f"wrote value {shared_value}")
            if self.waiting_writers > 0:
                self.can_write.notify()                   # next writer goes first
            else:
                self.can_read.notify_all()                # no writers waiting: wake all readers
            record(name, "idle", "leaves the monitor")


monitor = ReadersWriterMonitor()


# ------------------------------------------------------------------
# Reader and writer threads
# ------------------------------------------------------------------
def reader(reader_id):
    name = f"R{reader_id}"
    for _ in range(ROUNDS):
        time.sleep(random.uniform(0.05, 0.6))             # time before the next read
        monitor.start_read(name)
        try:
            _ = shared_value                              # read the shared value
            time.sleep(random.uniform(0.2, 0.5))          # simulate reading
        finally:
            monitor.end_read(name)


def writer(writer_id):
    global shared_value, last_written, last_writer
    name = f"W{writer_id}"
    for _ in range(ROUNDS):
        time.sleep(random.uniform(0.05, 0.6))
        monitor.start_write(name)
        try:
            shared_value += 1                             # only one writer can be here
            last_written = shared_value
            last_writer = name
            time.sleep(random.uniform(0.3, 0.5))          # simulate writing
        finally:
            monitor.end_write(name)


# ------------------------------------------------------------------
# HTML report: the page replays the events recorded above
# ------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Readers-Writers Problem - Monitor Solution</title>
<style>
  body { font-family: Arial, sans-serif; background: #eef0f4; color: #1f2937; margin: 0; }
  .top { background: #2b3a55; color: #fff; padding: 18px 30px; }
  .top h1 { font-size: 24px; margin: 0 0 6px; }
  .top p { margin: 0; font-size: 14px; }
  .ok { color: #5fe08a; font-weight: bold; }
  .bad { color: #ff7b86; font-weight: bold; }
  .main { padding: 20px 30px; }
  .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.12); padding: 16px 18px; margin-bottom: 16px; }
  .card h2 { font-size: 16px; margin: 0 0 12px; color: #12284c; }
  .bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .bar button { padding: 8px 18px; font-size: 15px; background: #f0f0f0; border: 1px solid #888; border-radius: 4px; cursor: pointer; }
  .bar select { padding: 6px; font-size: 15px; }
  .spacer { flex: 1; }
  .chip { font-size: 13px; padding: 3px 10px; border-radius: 4px; border: 1px solid #aaa; margin-left: 4px; }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .boxes { display: flex; flex-wrap: wrap; gap: 12px; }
  .box { width: 176px; padding: 14px 6px; text-align: center; border-radius: 6px; border: 2px solid #aaa; font-size: 18px; }
  .box b { display: block; font-size: 18px; }
  .box small { display: block; font-size: 12px; margin-top: 4px; }
  .idle { background: #e5e5e5; border-color: #aaa; }
  .waiting { background: #fdeeb4; border-color: #e0b81a; }
  .reading { background: #d3ecd7; border-color: #3aa655; }
  .writing { background: #f8d4d8; border-color: #dd4a58; }
  .finished { background: #cfe2ff; border-color: #3b82f6; }
  .locked { color: #dd3344; }
  .free { color: #198754; }
  .tl-row { display: flex; align-items: center; margin-bottom: 6px; }
  .tl-name { width: 38px; font-weight: bold; font-size: 14px; }
  .tl-track { position: relative; flex: 1; height: 22px; background: #eee; border-radius: 3px; }
  .seg { position: absolute; top: 0; height: 22px; }
  #playhead { position: absolute; top: -4px; width: 2px; background: #000; z-index: 5; }
  .tl-axis { display: flex; justify-content: space-between; margin-left: 38px; font-size: 12px; color: #555; }
  .logwrap { max-height: 300px; overflow-y: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; }
  th { text-align: left; background: #edf0f5; padding: 6px 8px; position: sticky; top: 0; }
  td { padding: 5px 8px; border-bottom: 1px solid #e3e3e3; }
  tr.now td { font-weight: bold; }
  ul.checks { margin: 0; padding-left: 20px; line-height: 1.7; }
</style>
</head>
<body>
<div class="top">
  <h1>Readers-Writers Problem - monitor solution, writer preference (replay of a real run)</h1>
  <p>__SUBTITLE__</p>
</div>
<div class="main">

<div class="card bar">
  <button id="play">Play</button><button id="step">Step</button><button id="reset">Reset</button>
  <span>speed</span>
  <select id="speed"><option value="0.5">0.5x</option><option value="1" selected>1x</option>
    <option value="2">2x</option><option value="4">4x</option></select>
  <span>clock: <b id="clock">0 ms</b></span>
  <span>event <b id="evno">0</b> / <span id="evtotal"></span></span>
  <span class="spacer"></span>
  <span>
    <span class="chip idle">idle</span><span class="chip waiting">waiting</span><span class="chip reading">reading</span><span class="chip writing">writing</span><span class="chip finished">finished</span>
  </span>
</div>

<div class="row2">
  <div class="card"><h2>Readers</h2><div class="boxes" id="readers"></div></div>
  <div class="card"><h2>Writers</h2><div class="boxes" id="writers"></div></div>
</div>

<div class="row2">
  <div class="card">
    <h2>Shared resource (critical section)</h2>
    <p>status: <span id="status"></span></p>
    <p>value: <b id="value" style="font-size:28px">0</b></p>
    <p>last written by: <span id="lastw">-</span></p>
  </div>
  <div class="card">
    <h2>Monitor state</h2>
    <p>active_readers: <b id="m_ar">0</b></p>
    <p>writer_active: <b id="m_wa">False</b></p>
    <p>waiting_writers: <b id="m_ww">0</b></p>
    <p>readers held back: <b id="m_hb">none</b></p>
  </div>
</div>

<div class="card">
  <h2>Timeline (RES row = who holds the resource; yellow = waiting, green = reading, red = writing)</h2>
  <div id="timeline" style="position:relative"></div>
  <div class="tl-axis"><span>0 ms</span><span id="endms"></span></div>
</div>

<div class="card">
  <h2>Event log recorded by the program</h2>
  <div class="logwrap" id="logwrap">
    <table><thead><tr><th>#</th><th>time</th><th>who</th><th>state</th><th>active_readers</th>
    <th>writer_active</th><th>waiting_writers</th><th>held back</th><th>note</th></tr></thead>
    <tbody id="log"></tbody></table>
  </div>
</div>

<div class="card">
  <h2>Automatic verification checks</h2>
  <ul class="checks">__CHECKS__</ul>
  <p style="font-size:13px;color:#555">Generated __GENERATED__. The page replays the events recorded by the Python program;
  the thread order can be different in every run.</p>
</div>

</div>
<script>
const EVENTS = __EVENTS__;
const READERS = __READERS__;
const WRITERS = __WRITERS__;
const TOTAL = EVENTS.length ? Math.max(EVENTS[EVENTS.length - 1].t, 1) : 1;
const COLORS = { waiting: "#e0b81a", reading: "#3aa655", writing: "#dd4a58" };
let idx = 0, clock = 0, timer = null;

function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function $(id) { return document.getElementById(id); }
function listOrNone(a) { return a.length ? a.join(", ") : "none"; }

// ---- static timeline, built once from the recorded events ----
function buildTimeline() {
  const names = ["RES"].concat(READERS, WRITERS);
  let out = "";
  names.forEach(function (n) {
    out += '<div class="tl-row"><div class="tl-name">' + n + '</div><div class="tl-track" id="tr-' + n + '"></div></div>';
  });
  $("timeline").innerHTML = out;
  function addSeg(track, from, to, color) {
    if (to <= from) return;
    const d = document.createElement("div");
    d.className = "seg";
    d.style.left = (from / TOTAL * 100) + "%";
    d.style.width = ((to - from) / TOTAL * 100) + "%";
    d.style.background = color;
    $(track).appendChild(d);
  }
  names.forEach(function (n) {
    if (n === "RES") {
      EVENTS.forEach(function (e, i) {
        const end = i + 1 < EVENTS.length ? EVENTS[i + 1].t : TOTAL;
        if (e.wa !== "no") addSeg("tr-RES", e.t, end, COLORS.writing);
        else if (e.rl.length > 0) addSeg("tr-RES", e.t, end, COLORS.reading);
      });
    } else {
      const mine = EVENTS.filter(function (e) { return e.who === n; });
      mine.forEach(function (e, i) {
        const end = i + 1 < mine.length ? mine[i + 1].t : TOTAL;
        if (COLORS[e.state]) addSeg("tr-" + n, e.t, end, COLORS[e.state]);
      });
    }
  });
  const ph = document.createElement("div");
  ph.id = "playhead";
  ph.style.height = (names.length * 28 + 4) + "px";
  $("timeline").appendChild(ph);
}

function movePlayhead() {
  const first = document.querySelector(".tl-track");
  const tl = $("timeline").getBoundingClientRect();
  const tr = first.getBoundingClientRect();
  $("playhead").style.left = (tr.left - tl.left + tr.width * Math.min(clock / TOTAL, 1)) + "px";
}

// ---- show the state after the first idx events ----
function render() {
  const st = {};
  READERS.concat(WRITERS).forEach(function (w) { st[w] = { state: "idle", value: 0 }; });
  let last = null;
  for (let i = 0; i < idx; i++) {
    const e = EVENTS[i];
    st[e.who] = { state: e.state, value: e.value };
    last = e;
  }
  function boxes(list) {
    return list.map(function (w) {
      const s = st[w];
      let text = s.state, extra = "";
      if (s.state === "finished") text = "finished " + (w[0] === "R" ? "reading" : "writing");
      if (w[0] === "R" && s.state === "reading") extra = "<small>sees value " + s.value + "</small>";
      if (w[0] === "W" && s.state === "finished") extra = "<small>value is now " + s.value + "</small>";
      return '<div class="box ' + s.state + '"><b>' + w + "</b>" + text + extra + "</div>";
    }).join("");
  }
  $("readers").innerHTML = boxes(READERS);
  $("writers").innerHTML = boxes(WRITERS);

  let status = '<span class="free">FREE</span>';
  if (last && last.wa !== "no") status = '<span class="locked">BEING WRITTEN by ' + last.wa + " (exclusive)</span>";
  else if (last && last.rl.length > 0) status = '<span class="free">BEING READ by ' + last.rl.join(", ") + " (" + last.rl.length + " at once)</span>";
  $("status").innerHTML = status;
  $("value").textContent = last ? last.value : 0;
  $("lastw").textContent = last ? last.last_writer : "-";

  $("m_ar").textContent = last ? last.ar : 0;
  $("m_wa").textContent = last && last.wa !== "no" ? "True" : "False";
  $("m_ww").textContent = last ? last.ww : 0;
  $("m_hb").textContent = last ? listOrNone(last.hb) : "none";

  $("clock").textContent = Math.round(clock) + " ms";
  $("evno").textContent = idx;
  let rows = "";
  for (let i = 0; i < idx; i++) {
    const e = EVENTS[i];
    rows += "<tr" + (i === idx - 1 ? ' class="now"' : "") + "><td>" + e.n + "</td><td>" + e.t + " ms</td><td>" + e.who +
      "</td><td>" + e.state + "</td><td>" + e.ar + "</td><td>" + (e.wa !== "no" ? "True (" + esc(e.wa) + ")" : "False") +
      "</td><td>" + e.ww + "</td><td>" + esc(listOrNone(e.hb)) + "</td><td>" + esc(e.note) + "</td></tr>";
  }
  $("log").innerHTML = rows;
  $("logwrap").scrollTop = $("logwrap").scrollHeight;
  movePlayhead();
}

// ---- controls ----
function stop() { clearInterval(timer); timer = null; $("play").textContent = "Play"; }
function tick() {
  clock += 40 * parseFloat($("speed").value);
  while (idx < EVENTS.length && EVENTS[idx].t <= clock) idx++;
  if (idx >= EVENTS.length && clock >= TOTAL) { clock = TOTAL; stop(); }
  render();
}
$("play").onclick = function () {
  if (timer) { stop(); return; }
  if (idx >= EVENTS.length) { idx = 0; clock = 0; }
  $("play").textContent = "Pause";
  timer = setInterval(tick, 40);
};
$("step").onclick = function () {
  stop();
  if (idx < EVENTS.length) { idx++; clock = EVENTS[idx - 1].t; render(); }
};
$("reset").onclick = function () { stop(); idx = 0; clock = 0; render(); };
window.onresize = movePlayhead;

$("evtotal").textContent = EVENTS.length;
$("endms").textContent = TOTAL + " ms";
buildTimeline();
render();
</script>
</body>
</html>
"""


def make_html(filename, checks):
    """Fill the page template with the recorded events and save it."""
    readers = [f"R{i}" for i in range(1, NUM_READERS + 1)]
    writers = [f"W{i}" for i in range(1, NUM_WRITERS + 1)]
    passed = sum(1 for _, ok in checks if ok)
    if passed == len(checks):
        verdict = f'<span class="ok">all {len(checks)} checks passed</span>'
    else:
        verdict = f'<span class="bad">{len(checks) - passed} of {len(checks)} checks FAILED</span>'
    subtitle = (f"{NUM_READERS} readers, {NUM_WRITERS} writers, {ROUNDS} rounds each | "
                f"{len(events)} events recorded | max readers at once: {max_readers} | "
                f"final value {shared_value} (expected {NUM_WRITERS * ROUNDS}) | {verdict}")
    check_items = "".join(
        f'<li><span class="{"ok" if ok else "bad"}" style="color:{"#198754" if ok else "#dc3545"}">'
        f'{"PASS" if ok else "FAIL"}</span> - {html.escape(text)}</li>' for text, ok in checks)
    page = (PAGE
            .replace("__EVENTS__", json.dumps(events))
            .replace("__READERS__", json.dumps(readers))
            .replace("__WRITERS__", json.dumps(writers))
            .replace("__SUBTITLE__", subtitle)
            .replace("__CHECKS__", check_items)
            .replace("__GENERATED__", datetime.now().strftime("%d-%m-%Y %H:%M:%S")))
    with open(filename, "w", encoding="utf-8") as f:
        f.write(page)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
if __name__ == "__main__":
    threads = [threading.Thread(target=reader, args=(i,)) for i in range(1, NUM_READERS + 1)]
    threads += [threading.Thread(target=writer, args=(i,)) for i in range(1, NUM_WRITERS + 1)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = NUM_WRITERS * ROUNDS
    checks = [
        ("At most one writer was ever active", max_writers <= 1),
        ("A reader and a writer were never active together", overlap_count == 0),
        ("Active reader/writer counts never went negative", negative_count == 0),
        ("Every reader finished all its rounds", reads_done == NUM_READERS * ROUNDS),
        ("Every writer finished all its rounds", writes_done == NUM_WRITERS * ROUNDS),
        ("Final value equals the expected value", shared_value == expected),
        ("Final value equals the last successful write", shared_value == last_written),
        ("Monitor ended clean (no readers, no writer, nobody waiting)",
         monitor.active_readers == 0 and not monitor.writer_active
         and monitor.waiting_writers == 0 and not monitor.held_back),
    ]

    print("\nFinal shared value:", shared_value, f"(expected {expected})")
    print("Max readers at once:", max_readers)
    for text, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + text)

    folder = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(folder, "readers_writers_monitor.html")
    make_html(out_file, checks)
    print("HTML file created:", out_file)

    # open the page in the default web browser
    if AUTO_OPEN_HTML:
        try:
            webbrowser.open(Path(out_file).as_uri())
        except Exception:
            print("Could not open the browser automatically - open the HTML file by hand.")

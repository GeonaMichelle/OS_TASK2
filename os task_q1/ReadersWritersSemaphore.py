"""
Readers-Writers Problem (reader-preference) using semaphores.

Run:  python ReadersWritersSemaphore.py
Creates readers_writers_semaphore.html (an animated replay of this run)
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
NUM_READERS = 4
NUM_WRITERS = 2
ROUNDS = 2                        # how many times each thread repeats its work

# ------------------------------------------------------------------
# Shared resource and synchronization semaphores
# ------------------------------------------------------------------
shared_value = 0                  # the shared resource
read_count = 0                    # readers currently using the resource

mutex = threading.Semaphore(1)    # protects read_count
wrt = threading.Semaphore(1)      # exclusive access to the shared resource

# ------------------------------------------------------------------
# Execution log and state tracking (protected by its own lock)
# ------------------------------------------------------------------
log_lock = threading.Lock()
events = []                       # every real event is stored here (used for the HTML)
active_readers = 0                # readers inside the critical section now
active_writers = 0                # writers inside the critical section now
writing_now = "no"                # name of the writer currently writing
holder_now = "none"               # who holds the resource: "readers", "W1", ... or "none"
last_writer = "-"                 # last writer that changed the value
last_written = None               # value of the last successful write
failures = []                     # broken rules are recorded here
start_time = time.time()


def record(who, state, note="", holder=None):
    """Log one event at the moment it happens and check the rules.
    state is one of: waiting, reading, writing, finished, idle."""
    global active_readers, active_writers, writing_now, holder_now
    with log_lock:
        is_reader = who.startswith("R")

        if state == "reading":
            active_readers += 1
        elif state == "writing":
            active_writers += 1
            writing_now = who
        elif state == "finished":
            if is_reader:
                active_readers -= 1
            else:
                active_writers -= 1
                writing_now = "no"
        if holder is not None:
            holder_now = holder

        # ---- automatic verification ----
        if active_writers > 1:
            failures.append(f"{who}: more than one writer active")
        if active_writers > 0 and active_readers > 0:
            failures.append(f"{who}: reader and writer active together")
        if active_readers < 0 or active_writers < 0:
            failures.append(f"{who}: negative active count")

        ms = int(round((time.time() - start_time) * 1000))
        events.append({"n": len(events) + 1, "t": ms, "who": who, "state": state,
                       "readers": active_readers, "writer": writing_now,
                       "holder": holder_now, "value": shared_value,
                       "last_writer": last_writer, "note": note})
        print(f"[{ms:5d} ms] {who:3} {state:9} {note:38} "
              f"readers={active_readers} writer={writing_now}")


# ------------------------------------------------------------------
# Reader thread
# ------------------------------------------------------------------
def reader(reader_id):
    global read_count
    name = f"R{reader_id}"
    for _ in range(ROUNDS):
        time.sleep(random.uniform(0.1, 0.8))              # idle time before next read
        record(name, "waiting", "wants to read")

        # ---- entry section ----
        mutex.acquire()                                   # lock read_count
        try:
            read_count += 1
            if read_count == 1:                           # first reader blocks writers
                wrt.acquire()
        finally:
            mutex.release()

        # ---- critical section: many readers can be here together ----
        try:
            value = shared_value
            record(name, "reading", f"reads value {value}", holder="readers")
            time.sleep(random.uniform(0.4, 0.9))          # simulate reading
            record(name, "finished", f"finished reading value {value}")
        finally:
            # ---- exit section ----
            mutex.acquire()
            try:
                read_count -= 1
                if read_count == 0:                       # last reader lets writers in
                    record(name, "idle", "last reader releases the resource", holder="none")
                    wrt.release()
                else:
                    record(name, "idle", f"{read_count} reader(s) still reading")
            finally:
                mutex.release()


# ------------------------------------------------------------------
# Writer thread
# ------------------------------------------------------------------
def writer(writer_id):
    global shared_value, last_written, last_writer
    name = f"W{writer_id}"
    for _ in range(ROUNDS):
        time.sleep(random.uniform(0.1, 0.8))
        record(name, "waiting", "wants to write")

        wrt.acquire()                                     # exclusive access
        try:
            # ---- critical section: only this writer, no readers ----
            record(name, "writing", "has exclusive access", holder=name)
            shared_value += 10                            # each write adds 10
            last_written = shared_value
            last_writer = name
            time.sleep(random.uniform(0.4, 0.9))          # simulate writing
            record(name, "finished", f"wrote value {shared_value}")
            record(name, "idle", "releases the resource", holder="none")
        finally:
            wrt.release()


# ------------------------------------------------------------------
# HTML report: the page replays the events recorded above
# ------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Readers-Writers Problem - Semaphore Solution</title>
<style>
  body { font-family: Arial, sans-serif; background: #eef0f4; color: #1f2937; margin: 0; padding: 20px 24px; }
  h1 { font-size: 22px; margin: 0 0 6px; color: #12284c; }
  .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.12); padding: 16px 18px; margin-bottom: 16px; }
  .card h2 { font-size: 16px; margin: 0 0 12px; color: #12284c; }
  .result { display: inline-block; color: #fff; padding: 6px 12px; border-radius: 4px; margin-top: 6px; }
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
</style>
</head>
<body>
<h1>Readers-Writers Problem - Semaphore Solution</h1>
<p style="margin:0 0 6px"><b>Generated:</b> __GENERATED__ &nbsp; <b>Final shared value:</b> __FINAL__
&nbsp; <b>Events recorded:</b> __COUNT__</p>
<div class="result" style="background:__COLOR__">__SUMMARY__</div>
<p style="font-size:13px;color:#555">This page is a replay of the events recorded by the Python program during its run.
The thread order can be different in every run.</p>

<div class="card bar">
  <button id="play">Play</button><button id="step">Step</button><button id="reset">Reset</button>
  <span>speed</span>
  <select id="speed"><option value="0.5">0.5x</option><option value="1" selected>1x</option>
    <option value="2">2x</option><option value="4">4x</option></select>
  <span>clock: <b id="clock">0 ms</b></span>
  <span>event <b id="evno">0</b> / <span id="evtotal"></span></span>
  <span class="spacer"></span>
  <span>
    <span class="chip idle">idle</span><span class="chip waiting">waiting</span><span class="chip reading">reading</span><span class="chip writing">writing</span><span class="chip finished">finished / released</span>
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
    <p>readers currently reading: <span id="rcount">0</span></p>
  </div>
  <div class="card"><h2>Who is waiting</h2><p id="waiting">nobody</p></div>
</div>

<div class="card">
  <h2>Timeline (RES row = who holds the resource; yellow = waiting, green = reading, red = writing)</h2>
  <div id="timeline" style="position:relative"></div>
  <div class="tl-axis"><span>0 ms</span><span id="endms"></span></div>
</div>

<div class="card">
  <h2>Event log recorded by the program</h2>
  <div class="logwrap" id="logwrap">
    <table><thead><tr><th>#</th><th>time</th><th>who</th><th>state</th><th>readers reading</th>
    <th>writer writing</th><th>resource held by</th><th>note</th></tr></thead>
    <tbody id="log"></tbody></table>
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
        if (e.holder === "readers") addSeg("tr-RES", e.t, end, COLORS.reading);
        else if (e.holder !== "none") addSeg("tr-RES", e.t, end, COLORS.writing);
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

// ---- state after the first n events ----
function render() {
  const st = {};
  READERS.concat(WRITERS).forEach(function (w) { st[w] = { state: "idle", value: 0, order: -1 }; });
  let last = null;
  for (let i = 0; i < idx; i++) {
    const e = EVENTS[i];
    st[e.who] = { state: e.state, value: e.value, order: i };
    last = e;
  }
  function label(w, s) {
    if (s === "finished") return "finished " + (w[0] === "R" ? "reading" : "writing");
    return s;
  }
  function boxes(list) {
    return list.map(function (w) {
      const s = st[w];
      let extra = "";
      if (w[0] === "W" && s.state === "finished") extra = "<small>value is now " + s.value + "</small>";
      return '<div class="box ' + s.state + '"><b>' + w + "</b>" + label(w, s.state) + extra + "</div>";
    }).join("");
  }
  $("readers").innerHTML = boxes(READERS);
  $("writers").innerHTML = boxes(WRITERS);

  const holder = last ? last.holder : "none";
  let status;
  if (holder === "none") status = '<span class="free">FREE</span>';
  else if (holder === "readers") status = '<span class="locked">HELD by readers (shared reading)</span>';
  else status = '<span class="locked">LOCKED by ' + holder + (st[holder].state === "finished"
        ? " - write finished, not released yet" : " - writing") + "</span>";
  $("status").innerHTML = status;
  $("value").textContent = last ? last.value : 0;
  $("lastw").textContent = last ? last.last_writer : "-";
  $("rcount").textContent = last ? last.readers : 0;

  const waiting = READERS.concat(WRITERS).filter(function (w) { return st[w].state === "waiting"; })
    .sort(function (a, b) { return st[a].order - st[b].order; });
  $("waiting").textContent = waiting.length ? waiting.join(", ") : "nobody";

  $("clock").textContent = Math.round(clock) + " ms";
  $("evno").textContent = idx;
  let rows = "";
  for (let i = 0; i < idx; i++) {
    const e = EVENTS[i];
    rows += "<tr" + (i === idx - 1 ? ' class="now"' : "") + "><td>" + e.n + "</td><td>" + e.t + " ms</td><td>" + e.who +
      "</td><td>" + e.state + "</td><td>" + e.readers + "</td><td>" + esc(e.writer) + "</td><td>" +
      esc(e.holder) + "</td><td>" + esc(e.note) + "</td></tr>";
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


def make_html(filename, passed, summary):
    """Fill the page template with the recorded events and save it."""
    readers = [f"R{i}" for i in range(1, NUM_READERS + 1)]
    writers = [f"W{i}" for i in range(1, NUM_WRITERS + 1)]
    page = (PAGE
            .replace("__EVENTS__", json.dumps(events))
            .replace("__READERS__", json.dumps(readers))
            .replace("__WRITERS__", json.dumps(writers))
            .replace("__GENERATED__", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
            .replace("__FINAL__", str(shared_value))
            .replace("__COUNT__", str(len(events)))
            .replace("__COLOR__", "#198754" if passed else "#dc3545")
            .replace("__SUMMARY__", html.escape(summary)))
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

    # Final checks
    if shared_value != last_written:
        failures.append("final shared value does not match last successful write")
    if active_readers != 0 or active_writers != 0:
        failures.append("some thread did not leave the critical section")

    passed = len(failures) == 0
    if passed:
        summary = "PASSED: no overlap of readers and writers, only one writer at a time, counts never negative."
    else:
        summary = "FAILED: " + "; ".join(failures)

    print("\nFinal shared value:", shared_value)
    print(summary)

    folder = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(folder, "readers_writers_semaphore.html")
    make_html(out_file, passed, summary)
    print("HTML file created:", out_file)

    # open the page in the default web browser
    if AUTO_OPEN_HTML:
        try:
            webbrowser.open(Path(out_file).as_uri())
        except Exception:
            print("Could not open the browser automatically - open the HTML file by hand.")

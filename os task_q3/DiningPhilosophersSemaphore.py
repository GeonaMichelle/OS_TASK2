"""
Dining Philosophers Problem (4 philosophers) using SEMAPHORES.

Rules of the table
  - 4 philosophers sit around a table, with one fork between each pair (4 forks).
  - To eat, a philosopher needs BOTH the left fork and the right fork.
  - Philosopher i uses left fork F[i] and right fork F[(i+1) % 4].

Semaphores used
  - fork[0..3] = Semaphore(1)  : one binary semaphore per fork (1 = free, 0 = in use)
  - room       = Semaphore(3)  : at most N-1 = 3 philosophers may try to pick up forks

Why there is no deadlock
  Deadlock needs a circular wait: every philosopher holding his left fork and
  waiting for his right fork. The room semaphore lets only 3 of the 4 philosophers
  compete at the same time, so at least one of them can always get both forks,
  eat, and put the forks back. The circle can never be completed.

Starvation note
  This solution is deadlock-free, but it does not strictly promise fairness:
  the order in which waiting threads get the room semaphore is decided by Python
  and the OS. In practice every philosopher gets a turn here, and the program
  checks that every philosopher finished all of his meals.

Run:  python DiningPhilosophersSemaphore.py
Creates dining_philosophers_semaphore.html (an animated replay of this run)
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
NUM_PHILOSOPHERS = 4
MEALS = 3                         # how many times each philosopher eats

# ------------------------------------------------------------------
# Semaphores
# ------------------------------------------------------------------
fork = [threading.Semaphore(1) for _ in range(NUM_PHILOSOPHERS)]   # one per fork
room = threading.Semaphore(NUM_PHILOSOPHERS - 1)                   # N-1 places at the table

# ------------------------------------------------------------------
# Execution log and independent rule checking (own lock)
# ------------------------------------------------------------------
log_lock = threading.Lock()
events = []                                        # every real event is stored here (used for the HTML)
fork_owner = [None] * NUM_PHILOSOPHERS             # who holds each fork right now
eating_now = set()                                 # philosophers who are eating right now
in_room = 0                                        # philosophers inside the room right now
max_in_room = 0
meals_eaten = {f"P{i}": 0 for i in range(NUM_PHILOSOPHERS)}
problems = {"fork_shared": 0, "neighbours_ate": 0, "ate_without_forks": 0, "room_full": 0}
start_time = time.time()


def record(who, state, note, take=None, drop=None, room_change=0):
    """Log one event at the moment it happens and check the rules.
    state: thinking, hungry, acquiring, eating or releasing.
    take / drop : number of the fork that was just picked up / is about to be put down.
    room_change : +1 when entering the room, -1 when leaving it."""
    global in_room, max_in_room
    with log_lock:
        me = int(who[1:])
        left, right = me, (me + 1) % NUM_PHILOSOPHERS

        if take is not None:
            if fork_owner[take] is not None:               # a fork can have only one owner
                problems["fork_shared"] += 1
            fork_owner[take] = who
        if drop is not None:
            fork_owner[drop] = None
        if room_change:
            in_room += room_change
            max_in_room = max(max_in_room, in_room)
            if in_room > NUM_PHILOSOPHERS - 1:
                problems["room_full"] += 1

        if state == "eating":
            if fork_owner[left] != who or fork_owner[right] != who:
                problems["ate_without_forks"] += 1
            for neighbour in (f"P{(me - 1) % NUM_PHILOSOPHERS}", f"P{(me + 1) % NUM_PHILOSOPHERS}"):
                if neighbour in eating_now:
                    problems["neighbours_ate"] += 1
            eating_now.add(who)
            meals_eaten[who] += 1
        else:
            eating_now.discard(who)

        ms = int(round((time.time() - start_time) * 1000))
        events.append({"n": len(events) + 1, "t": ms, "who": who, "state": state,
                       "forks": [o if o else "-" for o in fork_owner],
                       "eating": sorted(eating_now), "room": in_room, "note": note})
        print(f"[{ms:5d} ms] {who} {state:9} {note}")


# ------------------------------------------------------------------
# Philosopher thread
# ------------------------------------------------------------------
def philosopher(i):
    name = f"P{i}"
    left = i                                       # left fork number
    right = (i + 1) % NUM_PHILOSOPHERS             # right fork number

    for meal in range(1, MEALS + 1):
        time.sleep(random.uniform(0.1, 0.6))       # THINKING

        record(name, "hungry", f"is hungry (meal {meal}), waiting for a place at the table")
        room.acquire()                             # wait(room): only N-1 may enter
        record(name, "acquiring", f"entered the room, trying to take forks F{left} and F{right}",
               room_change=+1)

        fork[left].acquire()                       # wait(fork[left])
        record(name, "acquiring", f"picked up left fork F{left}", take=left)
        time.sleep(random.uniform(0.05, 0.2))      # small delay makes the overlap visible

        fork[right].acquire()                      # wait(fork[right])
        record(name, "acquiring", f"picked up right fork F{right}", take=right)

        # ---- critical section: eating (holds both forks) ----
        record(name, "eating", f"has both forks F{left} and F{right} and eats")
        time.sleep(random.uniform(0.3, 0.6))

        # ---- releasing: log first, then signal, so the log order stays true ----
        record(name, "releasing", f"puts down left fork F{left}", drop=left)
        fork[left].release()                       # signal(fork[left])
        record(name, "releasing", f"puts down right fork F{right}", drop=right)
        fork[right].release()                      # signal(fork[right])

        record(name, "thinking", "back to thinking, leaving the room", room_change=-1)
        room.release()                             # signal(room)


# ------------------------------------------------------------------
# HTML report: the page replays the events recorded above
# ------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Dining Philosophers (4) - Semaphore Solution</title>
<style>
  body { font-family: Arial, sans-serif; background: #eef0f4; color: #1f2937; margin: 0; }
  .top { background: #3b2a55; color: #fff; padding: 16px 28px; }
  .top h1 { font-size: 24px; margin: 0 0 8px; }
  .top p { margin: 0 0 4px; font-size: 14px; }
  .ok { color: #5fe08a; font-weight: bold; }
  .bad { color: #ff7b86; font-weight: bold; }
  .main { padding: 20px 28px; }
  .card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.12); padding: 16px 18px; margin-bottom: 16px; }
  .card h2 { font-size: 16px; margin: 0 0 12px; color: #12284c; }
  .bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .bar button { padding: 8px 18px; font-size: 15px; background: #f0f0f0; border: 1px solid #888; border-radius: 4px; cursor: pointer; }
  .bar select { padding: 6px; font-size: 15px; }
  .spacer { flex: 1; }
  .chip { font-size: 13px; padding: 3px 10px; border-radius: 4px; border: 1px solid #aaa; margin-left: 4px; }
  .row2 { display: grid; grid-template-columns: 1.15fr 1fr; gap: 16px; }
  .boxes { display: flex; flex-wrap: wrap; gap: 12px; }
  .box { width: 216px; min-height: 96px; padding: 12px 8px; text-align: center; border-radius: 6px; border: 2px solid #aaa; font-size: 18px; box-sizing: border-box; }
  .box b { display: block; font-size: 18px; }
  .box small { display: block; font-size: 12px; margin-top: 6px; }
  .fk { width: 196px; min-height: 76px; }
  .thinking { background: #e5e5e5; border-color: #aaa; }
  .hungry { background: #fdeeb4; border-color: #e0b81a; }
  .acquiring { background: #fde0c4; border-color: #f28c28; }
  .eating { background: #d3ecd7; border-color: #3aa655; }
  .releasing { background: #cfe2ff; border-color: #3b82f6; }
  .inuse { background: #f8d4d8; border-color: #dd4a58; }
  .free { background: #f6f6f6; border-color: #aaa; }
  .tl-row { display: flex; align-items: center; margin-bottom: 6px; }
  .tl-name { width: 38px; font-weight: bold; font-size: 14px; }
  .tl-track { position: relative; flex: 1; height: 22px; background: #eee; border-radius: 3px; }
  .seg { position: absolute; top: 0; height: 22px; min-width: 3px; }
  #playhead { position: absolute; top: -4px; width: 2px; background: #000; z-index: 5; }
  .tl-axis { display: flex; justify-content: space-between; margin-left: 38px; font-size: 12px; color: #555; }
  .logwrap { max-height: 300px; overflow-y: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 14px; }
  th { text-align: left; background: #edf0f5; padding: 6px 8px; position: sticky; top: 0; }
  td { padding: 5px 8px; border-bottom: 1px solid #e3e3e3; }
  tr.now td { font-weight: bold; }
  ul.checks { margin: 0; padding-left: 20px; line-height: 1.7; }
  .t p { margin: 8px 0; }
</style>
</head>
<body>
<div class="top">
  <h1>Dining Philosophers (4) - Semaphore Solution (replay of a real run)</h1>
  <p>Semaphores: fork[0..3] = 1 each, room = 3 (at most N-1 philosophers compete -&gt; no deadlock)</p>
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
    <span class="chip thinking">thinking</span><span class="chip hungry">hungry</span><span class="chip acquiring">acquiring forks</span><span class="chip eating">eating</span><span class="chip releasing">releasing</span>
  </span>
</div>

<div class="card"><h2>Philosophers</h2><div class="boxes" id="phils"></div></div>

<div class="row2">
  <div class="card"><h2>Forks (shared resources)</h2><div class="boxes" id="forks"></div></div>
  <div class="card t">
    <h2>Table state</h2>
    <p>eating now: <b id="t_eat">none</b></p>
    <p>hungry / acquiring: <span id="t_hungry">none</span></p>
    <p>in the room (limit __LIMIT__): <b id="t_room">0</b></p>
    <p>forks in use: <span id="t_forks">0 / __N__</span></p>
  </div>
</div>

<div class="card">
  <h2>Timeline (P rows: philosopher state; F rows: red = fork in use)</h2>
  <div id="timeline" style="position:relative"></div>
  <div class="tl-axis"><span>0 ms</span><span id="endms"></span></div>
</div>

<div class="card">
  <h2>Event log recorded by the program</h2>
  <div class="logwrap" id="logwrap">
    <table><thead><tr><th>#</th><th>time</th><th>who</th><th>state</th>__FORKHEADS__<th>eating</th><th>note</th></tr></thead>
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
const N = __N__;
const PH = __PHILS__;
const FK = __FORKNAMES__;
const TOTAL = EVENTS.length ? Math.max(EVENTS[EVENTS.length - 1].t, 1) : 1;
const COLORS = { hungry: "#e0b81a", acquiring: "#f28c28", eating: "#3aa655", releasing: "#3b82f6" };
let idx = 0, clock = 0, timer = null;

function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function $(id) { return document.getElementById(id); }
function listOrNone(a) { return a.length ? a.join(", ") : "none"; }

// ---- static timeline, built once from the recorded events ----
function buildTimeline() {
  const names = PH.concat(FK);
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
  PH.forEach(function (p) {
    const mine = EVENTS.filter(function (e) { return e.who === p; });
    mine.forEach(function (e, i) {
      const end = i + 1 < mine.length ? mine[i + 1].t : TOTAL;
      if (COLORS[e.state]) addSeg("tr-" + p, e.t, end, COLORS[e.state]);
    });
  });
  FK.forEach(function (f, k) {
    EVENTS.forEach(function (e, i) {
      const end = i + 1 < EVENTS.length ? EVENTS[i + 1].t : TOTAL;
      if (e.forks[k] !== "-") addSeg("tr-" + f, e.t, end, "#dd4a58");
    });
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
  PH.forEach(function (p) { st[p] = { state: "thinking", note: "" }; });
  let last = null;
  for (let i = 0; i < idx; i++) {
    const e = EVENTS[i];
    st[e.who] = { state: e.state, note: e.note };
    last = e;
  }
  $("phils").innerHTML = PH.map(function (p) {
    const s = st[p];
    return '<div class="box ' + s.state + '"><b>' + p + "</b>" + s.state + "<small>" + esc(s.note) + "</small></div>";
  }).join("");

  const forks = last ? last.forks : FK.map(function () { return "-"; });
  $("forks").innerHTML = FK.map(function (f, k) {
    return forks[k] === "-"
      ? '<div class="box fk free"><b>' + f + "</b>free</div>"
      : '<div class="box fk inuse"><b>' + f + "</b>held by " + forks[k] + "</div>";
  }).join("");

  const eat = last ? last.eating : [];
  $("t_eat").textContent = eat.length ? eat.join(", ") + " (" + eat.length + ")" : "none";
  const hungry = PH.filter(function (p) { return st[p].state === "hungry" || st[p].state === "acquiring"; });
  $("t_hungry").textContent = listOrNone(hungry);
  $("t_room").textContent = last ? last.room : 0;
  $("t_forks").textContent = forks.filter(function (x) { return x !== "-"; }).length + " / " + N;

  $("clock").textContent = Math.round(clock) + " ms";
  $("evno").textContent = idx;
  let rows = "";
  for (let i = 0; i < idx; i++) {
    const e = EVENTS[i];
    rows += "<tr" + (i === idx - 1 ? ' class="now"' : "") + "><td>" + e.n + "</td><td>" + e.t + " ms</td><td>" + e.who +
      "</td><td>" + e.state.toUpperCase() + "</td>" + e.forks.map(function (f) { return "<td>" + f + "</td>"; }).join("") +
      "<td>" + e.eating.length + "</td><td>" + esc(e.note) + "</td></tr>";
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


def make_html(filename, checks, deadlock):
    """Fill the page template with the recorded events and save it."""
    phils = [f"P{i}" for i in range(NUM_PHILOSOPHERS)]
    forks = [f"F{i}" for i in range(NUM_PHILOSOPHERS)]
    passed = sum(1 for _, ok in checks if ok)
    if passed == len(checks):
        verdict = '<span class="ok">all checks passed - no deadlock</span>'
    elif deadlock:
        verdict = '<span class="bad">DEADLOCK detected</span>'
    else:
        verdict = f'<span class="bad">{len(checks) - passed} of {len(checks)} checks FAILED</span>'
    meals = ", ".join(f"{p}={meals_eaten[p]}" for p in phils)
    subtitle = (f"{NUM_PHILOSOPHERS} philosophers, {MEALS} meals each | {len(events)} events recorded | "
                f"meals: {meals} | {verdict}")
    check_items = "".join(
        f'<li><span style="color:{"#198754" if ok else "#dc3545"};font-weight:bold">'
        f'{"PASS" if ok else "FAIL"}</span> - {html.escape(text)}</li>' for text, ok in checks)
    page = (PAGE
            .replace("__EVENTS__", json.dumps(events))
            .replace("__PHILS__", json.dumps(phils))
            .replace("__FORKNAMES__", json.dumps(forks))
            .replace("__FORKHEADS__", "".join(f"<th>{f}</th>" for f in forks))
            .replace("__N__", str(NUM_PHILOSOPHERS))
            .replace("__LIMIT__", str(NUM_PHILOSOPHERS - 1))
            .replace("__SUBTITLE__", subtitle)
            .replace("__CHECKS__", check_items)
            .replace("__GENERATED__", datetime.now().strftime("%d-%m-%Y %H:%M:%S")))
    with open(filename, "w", encoding="utf-8") as f:
        f.write(page)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
if __name__ == "__main__":
    # daemon threads: if a deadlock ever happened, the program could still finish
    threads = [threading.Thread(target=philosopher, args=(i,), daemon=True)
               for i in range(NUM_PHILOSOPHERS)]
    for t in threads:
        t.start()

    deadline = time.time() + 30                    # no progress for 30 s would mean deadlock
    for t in threads:
        t.join(max(0, deadline - time.time()))
    deadlock = any(t.is_alive() for t in threads)

    checks = [
        ("No fork was ever held by two philosophers at once", problems["fork_shared"] == 0),
        ("Two neighbours never ate at the same time", problems["neighbours_ate"] == 0),
        ("A philosopher ate only while holding both of his forks", problems["ate_without_forks"] == 0),
        (f"At most {NUM_PHILOSOPHERS - 1} philosophers were in the room at once (max seen: {max_in_room})",
         problems["room_full"] == 0 and max_in_room <= NUM_PHILOSOPHERS - 1),
        (f"Every philosopher ate all {MEALS} meals (no starvation in this run)",
         all(m == MEALS for m in meals_eaten.values())),
        ("No deadlock: every philosopher thread finished", not deadlock),
        ("At the end all forks are free and the room is empty",
         all(o is None for o in fork_owner) and in_room == 0),
    ]

    print()
    for text, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + text)
    print("Meals eaten:", meals_eaten)

    folder = os.path.dirname(os.path.abspath(__file__))
    out_file = os.path.join(folder, "dining_philosophers_semaphore.html")
    make_html(out_file, checks, deadlock)
    print("HTML file created:", out_file)

    # open the page in the default web browser
    if AUTO_OPEN_HTML:
        try:
            webbrowser.open(Path(out_file).as_uri())
        except Exception:
            print("Could not open the browser automatically - open the HTML file by hand.")

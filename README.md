
# OS Synchronization Assignment

Python implementations of two classic synchronization problems, each solved in two ways:

| Problem | Semaphore solution | Monitor solution |
|---|---|---|
| Readers-Writers | `ReadersWritersSemaphore.py` (reader preference) | `ReadersWritersMonitor.py` (writer preference) |
| Dining Philosophers (4) | `DiningPhilosophersSemaphore.py` (room semaphore, N-1) | `DiningPhilosophersMonitor.py` (state + condition variables) |

Every program uses only Python's standard library (`threading`, `time`, `random`, `html`, `json`, `os`, `datetime`, `webbrowser`, `pathlib`). No external packages, Flask or frameworks are needed.

**Name:** _your name_  **USN:** _your USN_  **Course:** Operating Systems  **Section:** _your section_

---

## Folder structure

```
OS-Synchronization-Assignment/
├── README.md
├── readers_writers/
│   ├── semaphore/
│   │   ├── ReadersWritersSemaphore.py
│   │   └── readers_writers_semaphore.html      (generated)
│   └── monitor/
│       ├── ReadersWritersMonitor.py
│       └── readers_writers_monitor.html        (generated)
└── dining_philosophers/
    ├── semaphore/
    │   ├── DiningPhilosophersSemaphore.py
    │   └── dining_philosophers_semaphore.html  (generated)
    └── monitor/
        ├── DiningPhilosophersMonitor.py
        └── dining_philosophers_monitor.html    (generated)
```

The `.html` file is created automatically in the same folder as its `.py` file every time the program runs.

---

## Requirements

- Python 3.8 or newer
- Any modern web browser (to view the HTML report)

---

## How to run (VS Code, Windows)

1. Open the `OS-Synchronization-Assignment` folder in VS Code (File -> Open Folder).
2. Open the terminal with `` Ctrl + ` ``.
3. Run one program, for example:

```
cd readers_writers\semaphore
python ReadersWritersSemaphore.py
```

If `python` is not recognised, use `py ReadersWritersSemaphore.py`.

The other three:

```
cd readers_writers\monitor
python ReadersWritersMonitor.py

cd dining_philosophers\semaphore
python DiningPhilosophersSemaphore.py

cd dining_philosophers\monitor
python DiningPhilosophersMonitor.py
```

On Mac/Linux use `python3` and `/` instead of `\`.

### Opening the HTML report

When a program finishes, it writes its HTML file and opens it in your default browser automatically. If it does not open, double-click the `.html` file in the same folder (or run `start <file>.html` in the Windows terminal). To turn off the automatic opening, set `AUTO_OPEN_HTML = False` near the top of the program.

Click **Play** on the page to watch the run, **Step** to go one event at a time, and **Reset** to start again.

---

## The HTML report

Each page is a replay of the events that the program recorded during its real run. Nothing is scripted or reconstructed afterwards: every event stores the true state (counts, fork owners, monitor variables) at the moment it happened. The page shows:

- Play / Step / Reset controls with a speed selector, a clock and an event counter
- Cards for each thread (reader, writer or philosopher) coloured by state
- The shared resource state (value, forks, monitor variables)
- A timeline with a moving playhead
- The full event log
- The result of the automatic verification checks

Thread order changes from run to run, so every run produces a different report. The synchronization rules hold in all of them.

---

## 1. Readers-Writers with semaphores

File: `readers_writers/semaphore/ReadersWritersSemaphore.py`

- `mutex = Semaphore(1)` protects the reader count `read_count`.
- `wrt = Semaphore(1)` gives exclusive access to the shared value.
- The **first** reader locks `wrt` for all readers; the **last** reader releases it.
- A writer locks `wrt` itself, so it excludes readers and other writers.
- This is the **reader-preference** solution, so a steady stream of readers can starve writers.

Settings at the top of the file: `NUM_READERS = 4`, `NUM_WRITERS = 2`, `ROUNDS = 2`. Each write adds 10.

## 2. Readers-Writers with a monitor

File: `readers_writers/monitor/ReadersWritersMonitor.py`

- The class `ReadersWriterMonitor` holds one lock, two condition variables (`can_read`, `can_write`) and the state (`active_readers`, `writer_active`, `waiting_writers`).
- **Writer preference:** a new reader waits if a writer is writing or waiting. When a writer finishes, the next waiting writer goes first; readers are woken only if no writer is waiting.
- Writers are protected from starvation; in this version readers can starve instead.

Settings: `NUM_READERS = 5`, `NUM_WRITERS = 2`, `ROUNDS = 3`. Each write adds 1.

## 3. Dining Philosophers with semaphores

File: `dining_philosophers/semaphore/DiningPhilosophersSemaphore.py`

- `fork[0..3] = Semaphore(1)`, one per fork.
- `room = Semaphore(3)` lets at most N-1 philosophers try to pick up forks at the same time.
- With at most 3 of 4 competing, a circular wait is impossible, so there is **no deadlock**.
- Fairness is not strictly guaranteed; the program checks that every philosopher finished all meals.

## 4. Dining Philosophers with a monitor

File: `dining_philosophers/monitor/DiningPhilosophersMonitor.py`

- The class `DiningMonitor` keeps `state[i]` (THINKING, HUNGRY, EATING) and one condition variable per philosopher.
- `pickup(i)` sets HUNGRY, calls `_test(i)`, and waits until the state becomes EATING.
- `putdown(i)` sets THINKING and tests both neighbours, waking them if they can now eat.
- `_test(i)`: a hungry philosopher eats only if both neighbours are not eating, so both forks are taken in one step. No philosopher ever holds one fork while waiting for the other, so there is **no deadlock**.

Settings for both dining programs: `NUM_PHILOSOPHERS = 4`, `MEALS = 3`.

---

## Automatic verification

Each program checks its own run and shows PASS/FAIL in the terminal and in the HTML report. If a check fails, the failure is reported instead of a success message.

| Program | Checks |
|---|---|
| Readers-Writers (semaphore) | at most one writer active; no reader and writer together; counts never negative; final value equals last write |
| Readers-Writers (monitor) | the above, plus every reader and writer finished all rounds, final value equals the expected value, and the monitor ended clean |
| Dining Philosophers (semaphore) | no fork shared; neighbours never eat together; eating only with both forks; at most 3 in the room; all meals eaten; no deadlock; everything released at the end |
| Dining Philosophers (monitor) | no fork shared; neighbours never eat together; valid state order thinking -> hungry -> eating -> thinking; at most 2 eating at once; all meals eaten; no deadlock; everybody thinking at the end |

The dining programs wait at most 30 seconds. If any philosopher thread is still running after that, the report shows a deadlock instead of hanging.

---

## Sample terminal output (Readers-Writers, semaphore)

```
[  120 ms] R3  waiting   wants to read                         readers=0 writers=0
[  120 ms] R3  reading   reads value 0                         readers=1 writers=0
[  270 ms] R4  reading   reads value 0                         readers=2 writers=0
...
[ 1910 ms] W1  writing   has exclusive access                  readers=0 writers=1

Final shared value: 40
PASSED: no overlap of readers and writers, only one writer at a time, counts never negative.
HTML file created: ...\readers_writers_semaphore.html
```

(Exact numbers differ in every run.)

---

## Notes and limitations

- Python has no `monitor` keyword. The monitor solutions use a class with a `threading.Lock` and `threading.Condition` objects, which is the standard way to build a monitor in Python.
- Threads use random sleep times to simulate work, so the order of events changes in every run. Correctness does not.
- Timing in the replay uses the real recorded timestamps; very close events can appear at the same millisecond.

---

## Short viva notes

- **Semaphore:** an integer used for `wait` (acquire) and `signal` (release). A value of 1 makes it a mutual-exclusion lock.
- **Monitor:** one lock plus condition variables plus the data they protect; only one thread is inside at a time.
- **Why `while` around `wait()`:** a woken thread must recheck its condition.
- **Race condition:** two threads change shared data at the same time, for example `read_count += 1` without `mutex`.
- **Deadlock:** threads wait for each other forever. Avoided here by the room semaphore (semaphore version) and by taking both forks at once (monitor version).
- **Starvation:** a thread waits indefinitely. Possible for writers in reader preference, for readers in writer preference.

Implement the **Readers–Writers Problem using Semaphores in Python** for an Operating Systems synchronization assignment.

- Use Python's built-in `threading`, `time`, `html`, and `datetime` modules only.
- Implement the standard first-reader/last-reader solution using two semaphores: `mutex` for protecting the reader count and `wrt` for exclusive access to the shared resource.
- Create 4 reader threads and 2 writer threads using simple functions and a shared integer variable.
- Allow multiple readers to read simultaneously, but never allow readers and writers to access the resource simultaneously or multiple writers to write together.
- Maintain an accurate, thread-safe execution log containing timestamps, thread names, events, reader/writer counts, and shared values.
- Automatically generate `readers_writers_semaphore.html` after all threads finish. Include the final shared value, synchronization verification status, and a chronological event table with yellow waiting rows, green started rows, and red finished rows.
- Verify synchronization using accurate event-state tracking. Never display success if a synchronization rule is violated.
- Keep the code simple, student-friendly, commented, and free of unnecessary features or external dependencies.
- Provide complete runnable code in `ReadersWritersSemaphore.py`, sample output, VS Code execution instructions, a brief explanation, and basic viva questions.
- Mention that the reader-preference solution may cause writer starvation if readers continuously arrive.

**Expected files:**
`ReadersWritersSemaphore.py` and automatically generated `readers_writers_semaphore.html` in the same folder.

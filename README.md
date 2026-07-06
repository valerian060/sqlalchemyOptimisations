# SQLAlchemy Core vs. ORM Performance Benchmark

A micro-benchmark suite designed to evaluate the CPU performance gains of bypassing the SQLAlchemy ORM layer in favor of **SQLAlchemy Core raw mappings** within short-lived, request-scoped database sessions (mimicking production web framework lifecycles).

---

## Benchmark Profile
* **Database Engine:** SQLite running entirely in RAM (`:memory:`)
* **Async Driver:** `aiosqlite`
* **Volume:** 10 sequential runs of 10,000 iterations each (100,000 total queries executed)
* **Session Lifecycle:** Fresh database session instantiated and destroyed *per iteration*

---

## Results

============================================================
--- FINAL AVERAGED RESULTS OVER 10 RUNS (10000 iterations/run) ---
============================================================
Method A: Core                      : 8.3187 seconds
Method B: Standard ORM              : 9.0759 seconds
Method C: ORM (populate_existing)   : 8.9205 seconds
Method D: ORM (no populate override): 8.6240 seconds
------------------------------------------------------------
Core Gain over Standard ORM         : 8.34% faster
Core Gain over Populate Existing    : 6.75% faster
============================================================


## Getting Started

### Prerequisites
Ensure the asynchronous database driver and toolkit are present in your local virtual environment:
```bash
pip install sqlalchemy aiosqlite

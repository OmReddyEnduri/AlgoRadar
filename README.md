# AlgoRadar

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Platforms: 10+](https://img.shields.io/badge/Platforms-10%2B%20Indexed-blueviolet.svg?style=for-the-badge)](https://github.com/OmReddyEnduri/AlgoRadar#platform-integration-matrix)
[![Storage: SQLite WAL](https://img.shields.io/badge/Storage-Local%20SQLite%20(WAL)-003B57.svg?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Telemetry: Zero](https://img.shields.io/badge/Telemetry-Zero%20%2F%20100%25%20Local-success.svg?style=for-the-badge)](https://github.com/OmReddyEnduri/AlgoRadar#key-features)

**A high-performance, terminal-based competitive programming contest radar and calendar workstation.**  
*Track, monitor, and synchronize rounds from Codeforces, LeetCode, AtCoder, CodeChef, HackerRank, and more.*

</div>

---

## Terminal Workstation Preview

```text
    ___   __             ___             __          
   /   | / /____ _____  /   \____ _____ / /____ _____
  / /| |/ // __ `/ __ \/ /| / __ `/ __ `/ // __ `/ __/
 / ___ / // /_/ / /_/ / ___/ /_/ / /_/ / // /_/ / /   
/_/  |_\_\\__, /\____/_/   \__,_/\__,_/_/ \__,_/_/    
         /____/                                       
  ⚡ High-Performance CP Contest Radar & Calendar Workstation ⚡

┌─ ⚡ Upcoming & Active Competitive Programming Contests ────────────────────────────────────────────────────────┐
│ ★ │ Platform     │ Contest Name                               │ Start Time (UTC) │ Duration │ Starts In / Status     │
├───┼──────────────┼────────────────────────────────────────────┼──────────────────┼──────────┼────────────────────────┤
│ ★ │ ⚡ Codeforces │ Codeforces Round 1000 (Div. 2)             │ Nov 22, 14:35    │ 2h 00m   │ in 1d 03h              │
│   │ 🔶 LeetCode   │ Weekly Contest 440                         │ Nov 23, 02:30    │ 1h 30m   │ in 1d 15h              │
│   │ 🔴 AtCoder    │ AtCoder Beginner Contest 392 (ABC 392)     │ Nov 23, 12:00    │ 1h 40m   │ in 2d 01h              │
│ ★ │ 🧑‍🍳 CodeChef   │ Starters 174 (Div. 1, 2, 3 & 4)            │ Nov 26, 14:30    │ 2h 00m   │ in 5d 03h              │
│   │ 🟩 HackerRank │ University CodeSprint 2026                 │ Nov 28, 16:00    │ 3d 00m   │ in 7d 05h              │
│   │ 🔶 LeetCode   │ Biweekly Contest 151                       │ Nov 29, 14:30    │ 1h 30m   │ in 8d 03h              │
└───┴──────────────┴────────────────────────────────────────────┴──────────────────┴──────────┴────────────────────────┘
Showing 6 of 24 contests. Export to your calendar: 'algoradar export -f ics -o contests.ics'
```

---

## Key Features

- ⚡ **Multi-Platform Concurrent Sync**: Parallel fetch engine scrapes and queries official REST APIs and GraphQL endpoints for **Codeforces**, **LeetCode**, **AtCoder**, **CodeChef**, and **HackerRank** with automatic universal fallback redundancy.
- 🛡️ **100% Local & Zero Telemetry**: Absolutely zero telemetry, analytics, user accounts, or external tracking. All contest data lives strictly inside an embedded SQLite database in your home directory (`~/.algoradar/algoradar.db`).
- ⏱️ **Live Countdown & Status Timers**: Instant human-readable countdowns (`in 3h 15m`, `in 42m`, `Running (ends in 1h 20m)`) with automated lifecycle updates (`UPCOMING`, `RUNNING`, `FINISHED`).
- 📅 **RFC 5545 iCalendar (.ics) Export**: One-click calendar generation for Google Calendar, Apple Calendar, and Microsoft Outlook, complete with automatic 15-minute pre-contest alarms and direct contest links.
- 🚀 **High-Performance Architecture**: SQLite configured with WAL (Write-Ahead Logging) mode and index-accelerated queries for sub-millisecond CLI startup and offline-first workflows.
- 🎨 **Rich Terminal Aesthetics**: Styled tables with unicode icons, platform-branded color coding, customizable limits, and plain ASCII fallbacks for basic shells.

---

## Architecture Overview

```
                      ┌────────────────────────────────────────────────────────┐
                      │                 ALGORADAR ENGINE                       │
                      └────────────────────────────────────────────────────────┘
                                                  │
            ┌─────────────────────────────────────┴─────────────────────────────────────┐
            ▼                                                                           ▼
┌───────────────────────┐                                                   ┌───────────────────────┐
│   PLATFORM ADAPTERS   │                                                   │   CLI & WORKSTATION   │
├───────────────────────┤                                                   ├───────────────────────┤
│ • Codeforces REST API │                                                   │ • algoradar list      │
│ • LeetCode GraphQL    │ ───► [ Concurrent ThreadPool ] ──┐                │ • algoradar now       │
│ • AtCoder Kenkoooo/Web│                                  │                │ • algoradar sync      │
│ • CodeChef Public API │ ───► [ Normalizer & Deduper ] ───┤                │ • algoradar export    │
│ • HackerRank API Feed │                                  ▼                │ • algoradar platforms │
│ • Kontests Fallback   │                        ┌───────────────────┐      │ • algoradar stats     │
└───────────────────────┘                        │ LOCAL SQLITE DB   │      └───────────────────────┘
                                                 │   (WAL Mode)      │                  ▲
                                                 │ ~/.algoradar/     │ ─────────────────┘
                                                 │   algoradar.db    │                  │
                                                 └───────────────────┘                  ▼
                                                           │                ┌───────────────────────┐
                                                           └──────────────► │  iCalendar (.ics)     │
                                                                            │  Google/Apple/Outlook │
                                                                            └───────────────────────┘
```

---

## Platform Integration Matrix

AlgoRadar natively syncs from 5 primary contest platforms and tracks over 10 competitive programming ecosystems:

| Platform | Code | Icon | Integration Mechanism | Contest Formats | Rate Limit / Cache Policy | Status |
| :--- | :---: | :---: | :--- | :--- | :--- | :---: |
| **Codeforces** | `CF` | ⚡ | Official REST API (`contest.list`) | Div. 1–4, Educational, Global Rounds | 5 req/s · SQLite Cached | 🟢 Operational |
| **LeetCode** | `LC` | 🔶 | Official GraphQL API | Weekly & Biweekly Contests | 10 req/s · SQLite Cached | 🟢 Operational |
| **AtCoder** | `AC` | 🔴 | Kenkoooo API & Web Engine | ABC (Beginner), ARC (Regular), AGC | 2 req/s · SQLite Cached | 🟢 Operational |
| **CodeChef** | `CC` | 🧑‍🍳 | Public REST API & Web Scraper | Starters (Div 1–4), Cook-Off, Lunchtime | 5 req/s · SQLite Cached | 🟢 Operational |
| **HackerRank** | `HR` | 🟩 | Public REST Contests Feed | University CodeSprint, Hackathons | 5 req/s · SQLite Cached | 🟢 Operational |
| **TopCoder** | `TC` | 🎯 | Aggregator Redundancy Engine | Single Round Matches (SRM), TCO | Fallback Sync | 🟢 Indexed |
| **HackerEarth** | `HE` | 🌍 | Aggregator Redundancy Engine | Circuits, Monthly Easy, Challenges | Fallback Sync | 🟢 Indexed |
| **Kaggle** | `KG` | 📊 | Competitions Feed | ML, Analytics & Code Challenges | Fallback Sync | 🟢 Indexed |
| **CS Academy** | `CSA`| 💡 | Aggregator Redundancy Engine | Algorithm Rounds, Interactive Contests| Fallback Sync | 🟢 Indexed |
| **DMOJ** | `DMOJ`| 🦉 | Aggregator Redundancy Engine | Monthly Contests, Olympiad Contests | Fallback Sync | 🟢 Indexed |
| **Project Euler**| `PE`| 📐 | Release Schedule Indexer | Algorithmic & Mathematical Problems | Fallback Sync | 🟢 Indexed |
| **Google Archive**| `GK`| 🌐 | Historical Indexer | Code Jam, Kick Start, Hash Code | Fallback Sync | 🟢 Indexed |

---

## Quickstart & Installation

### Prerequisites
- **Python 3.10+** (also tested on Python 3.9, 3.11, 3.12, 3.13)
- `pip` or `uv` package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/OmReddyEnduri/AlgoRadar.git
cd AlgoRadar

# Install locally in standard mode
pip install .

# Or install in editable / development mode
pip install -e ".[dev]"
```

Verify installation:
```bash
algoradar --version
```

---

## CLI Usage Guide

### 1. Synchronize Live Contests
Fetch contests from all supported platforms concurrently and cache them locally:
```bash
# Sync all platforms
algoradar sync

# Sync specific platforms only
algoradar sync --platform CF,LC
```

### 2. List Upcoming Contests
View scheduled contests with live countdowns and URLs:
```bash
# View top 15 upcoming contests
algoradar list

# Filter by platform (e.g., Codeforces and LeetCode)
algoradar list --platform CF,LC

# Adjust the result limit
algoradar list --limit 25

# Show only bookmarked favorite contests
algoradar list --favorites

# Include finished rounds from history
algoradar list --all
```

### 3. Check Live Contests
Inspect rounds that are in progress right now:
```bash
algoradar now
```

### 4. Export to iCalendar (.ics)
Export contests to standard iCalendar format for seamless sync with Google Calendar, Apple Calendar, or Outlook:
```bash
# Export all upcoming contests to 'contests.ics' with 15-minute start reminders
algoradar export --format ics --output contests.ics

# Export only LeetCode and Codeforces rounds
algoradar export --platform CF,LC --output cp_schedule.ics

# Set a custom pre-contest alarm (e.g., 30 minutes before start)
algoradar export --alarm 30 --output schedule.ics

# Export raw contest metadata as JSON
algoradar export --format json --output contests.json
```

### 5. Workstation Diagnostics & Platform Catalog
```bash
# View detailed platform catalog and capabilities
algoradar platforms

# View local SQLite database statistics and contest breakdown
algoradar stats
```

---

## Python API Usage

You can also import AlgoRadar directly into your own Python scripts:

```python
from algoradar.adapters import Aggregator
from algoradar.storage import Storage
from algoradar.calendar_sync import export_ics

# 1. Fetch contests across platforms
aggregator = Aggregator()
contests = aggregator.fetch_all(platform_ids=["codeforces", "leetcode"])

# 2. Persist to local SQLite WAL database
storage = Storage()
storage.save_contests(contests)

# 3. Retrieve upcoming contests
upcoming = storage.get_upcoming(limit=5)
for contest in upcoming:
    print(f"[{contest.platform.short_code}] {contest.name} -> {contest.starts_in_str()}")

# 4. Export to iCalendar (.ics)
export_ics(upcoming, output_path="my_calendar.ics", alarm_minutes=15)
```

---

## Running Tests

AlgoRadar includes a comprehensive suite of unit tests covering models, adapters, SQLite persistence, iCalendar generation, and CLI subcommands:

```bash
# Run test suite with unittest
python -m unittest discover -s tests -v

# Or run with pytest
pytest -v
```

---

## Contributing

Contributions, bug reports, and suggestions are warmly welcomed! Please read our [Contributing Guide](CONTRIBUTING.md) to get started.

To add a new platform adapter:
1. Subclass `BaseAdapter` in `algoradar/adapters/<platform>.py`.
2. Implement the `fetch_contests()` method.
3. Register the platform in `models.py` and `aggregator.py`.
4. Add unit test fixtures in `tests/test_adapters.py`.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.  
Copyright (c) 2026 OmReddyEnduri.

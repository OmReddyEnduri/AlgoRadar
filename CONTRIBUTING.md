# Contributing to AlgoRadar

Thank you for your interest in contributing to **AlgoRadar**!

AlgoRadar is a high-performance, terminal-based competitive programming radar and calendar workstation designed for competitive programmers, algorithm enthusiasts, and software engineers. We welcome bug reports, feature suggestions, new platform adapters, and pull requests.

---

## Code of Conduct & Core Philosophy

AlgoRadar adheres to three foundational design principles:
1. **100% Local & Offline-First**: All contest data is stored locally in an embedded SQLite database using WAL (Write-Ahead Logging) mode.
2. **Zero Telemetry**: No tracking, no analytics, no external telemetry pinging. User privacy is strictly respected.
3. **High Performance**: Terminal commands and dashboard renders must execute instantly with zero perceptual lag.

---

## Development Setup

### Prerequisites
- **Python 3.10+**
- `git`
- Modern terminal supporting UTF-8 and ANSI colors / Nerd Fonts (Windows Terminal, iTerm2, Alacritty, Kitty, WezTerm)

### Quick Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/OmReddyEnduri/AlgoRadar.git
   cd AlgoRadar
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   # On Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # On Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies in Editable Mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify the Test Suite**
   ```bash
   pytest
   ```

---

## Project Architecture

```
AlgoRadar/
├── algoradar/
│   ├── __init__.py           # Package version and exports
│   ├── models.py             # Domain models (Contest, Platform, ContestStatus)
│   ├── storage.py            # Local SQLite storage with WAL mode
│   ├── sync.py               # Concurrent multi-platform fetcher & synchronization
│   ├── calendar.py           # iCalendar (.ics) export engine
│   ├── cli.py                # Command-line interface and subcommands
│   ├── tui.py                # Terminal workstation dashboard (Rich / Textual)
│   └── adapters/             # Platform-specific contest adapters
│       ├── __init__.py
│       ├── base.py           # Abstract BaseAdapter specification
│       ├── codeforces.py     # Codeforces API adapter
│       ├── leetcode.py       # LeetCode GraphQL adapter
│       ├── atcoder.py        # AtCoder contest adapter
│       ├── codechef.py       # CodeChef contest adapter
│       └── hackerrank.py     # HackerRank contest adapter
├── tests/                    # Unit and integration test suite
├── pyproject.toml            # Build system and dependency specifications
├── README.md                 # Project documentation
├── CONTRIBUTING.md           # Contribution guidelines
└── LICENSE                   # MIT License
```

---

## Adding a New Platform Adapter

We actively welcome adapters for additional competitive programming platforms (e.g., TopCoder, CSES, Kaggle, Project Euler).

To implement a new adapter:
1. Create a new module in `algoradar/adapters/<platform_name>.py`.
2. Inherit from `BaseAdapter` defined in `algoradar.adapters.base`.
3. Implement the `fetch_contests() -> List[Contest]` method.
4. Normalize contest details into standard `Contest` domain objects with timezone-aware UTC timestamps.
5. Handle network timeouts and API errors gracefully without crashing the application.
6. Register the platform in `algoradar/models.py` (`PLATFORMS_MAP`).
7. Add corresponding test fixtures and unit tests in `tests/test_adapters.py`.

---

## Coding Standards

- **Type Annotations**: All function signatures and class definitions must include PEP 484 type hints.
- **Code Style**: Format code cleanly. We recommend `ruff` or `black` for formatting and `ruff check` for linting.
- **Testing**: Every bug fix or new feature must include accompanying unit tests. Ensure test coverage remains high.
- **Docstrings**: Provide clear Google-style or PEP 257 docstrings for all public modules, classes, and methods.

---

## Submitting Pull Requests

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/my-new-feature
   # or
   git checkout -b fix/resolve-timezone-bug
   ```
2. Commit your changes with clear, semantic commit messages:
   ```bash
   git commit -m "feat(adapters): add TopCoder contest adapter"
   ```
3. Push your branch to your fork:
   ```bash
   git push origin feat/my-new-feature
   ```
4. Open a Pull Request against the `main` branch of `OmReddyEnduri/AlgoRadar`.
5. Provide a summary of changes, motivation, and any testing performed in the PR description.

Thank you for helping make AlgoRadar the best contest workstation for developers worldwide!

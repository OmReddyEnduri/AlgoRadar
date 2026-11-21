"""AlgoRadar CLI & Workstation Terminal.

A high-performance, terminal-based competitive programming contest radar and calendar
workstation for Codeforces, LeetCode, AtCoder, CodeChef, HackerRank, and more.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence

# Check for rich library support with graceful ANSI fallback
try:
    from rich.align import Align
    from rich.box import DOUBLE_EDGE, HEAVY_EDGE, ROUNDED, SIMPLE
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.style import Style
    from rich.table import Table
    from rich.text import Text

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from algoradar.adapters import Aggregator, list_supported_platforms
from algoradar.calendar_sync import export_ics
from algoradar.models import (
    ATCODER,
    CODECHEF,
    CODEFORCES,
    HACKERRANK,
    LEETCODE,
    Contest,
    ContestStatus,
    Platform,
    get_platform,
)
from algoradar.storage import DEFAULT_DB_PATH, Storage

# Workstation metadata
BANNER_ART = r"""
    ___   __             ___             __          
   /   | / /____ _____  /   \____ _____ / /____ _____
  / /| |/ // __ `/ __ \/ /| / __ `/ __ `/ // __ `/ __/
 / ___ / // /_/ / /_/ / ___/ /_/ / /_/ / // /_/ / /   
/_/  |_\_\\__, /\____/_/   \__,_/\__,_/_/ \__,_/_/    
         /____/                                       
"""

TAGLINE = "⚡ High-Performance CP Contest Radar & Calendar Workstation ⚡"

PLATFORM_COLORS = {
    "codeforces": "bright_blue",
    "cf": "bright_blue",
    "leetcode": "yellow",
    "lc": "yellow",
    "atcoder": "red",
    "ac": "red",
    "codechef": "magenta",
    "cc": "magenta",
    "hackerrank": "green",
    "hr": "green",
    "topcoder": "cyan",
    "tc": "cyan",
    "hackerearth": "bright_magenta",
    "he": "bright_magenta",
    "kaggle": "blue",
    "kg": "blue",
    "csacademy": "bright_yellow",
    "csa": "bright_yellow",
    "dmoj": "bright_red",
    "projecteuler": "white",
}

# Extended registry of 10+ platforms supported or indexed by AlgoRadar
SUPPORTED_PLATFORMS_CATALOG = [
    {
        "id": "codeforces",
        "name": "Codeforces",
        "code": "CF",
        "icon": "⚡",
        "type": "Live Native API",
        "formats": "Div 1–4, Educational, Global, Div 3/4 unrated",
        "url": "https://codeforces.com",
    },
    {
        "id": "leetcode",
        "name": "LeetCode",
        "code": "LC",
        "icon": "🔶",
        "type": "Live GraphQL API",
        "formats": "Weekly & Biweekly Contests, Global Rankings",
        "url": "https://leetcode.com",
    },
    {
        "id": "atcoder",
        "name": "AtCoder",
        "code": "AC",
        "icon": "🔴",
        "type": "Live Adapter / RSS",
        "formats": "ABC (Beginner), ARC (Regular), AGC (Grand)",
        "url": "https://atcoder.jp",
    },
    {
        "id": "codechef",
        "name": "CodeChef",
        "code": "CC",
        "icon": "🧑‍🍳",
        "type": "Live REST API",
        "formats": "Starters (Div 1–4), Cook-Off, Lunchtime",
        "url": "https://www.codechef.com",
    },
    {
        "id": "hackerrank",
        "name": "HackerRank",
        "code": "HR",
        "icon": "🟩",
        "type": "Live API & Feed",
        "formats": "University CodeSprint, Hackathons, Skills",
        "url": "https://www.hackerrank.com",
    },
    {
        "id": "topcoder",
        "name": "TopCoder",
        "code": "TC",
        "icon": "🎯",
        "type": "Aggregator Engine",
        "formats": "Single Round Matches (SRM), TCO, Marathons",
        "url": "https://www.topcoder.com",
    },
    {
        "id": "hackerearth",
        "name": "HackerEarth",
        "code": "HE",
        "icon": "🌍",
        "type": "Aggregator Engine",
        "formats": "Circuits, Monthly Easy, Corporate Challenges",
        "url": "https://www.hackerearth.com",
    },
    {
        "id": "kaggle",
        "name": "Kaggle",
        "code": "KG",
        "icon": "📊",
        "type": "Competitions Feed",
        "formats": "Machine Learning, Analytics & Code Competitions",
        "url": "https://www.kaggle.com",
    },
    {
        "id": "csacademy",
        "name": "CS Academy",
        "code": "CSA",
        "icon": "💡",
        "type": "Aggregator Engine",
        "formats": "Algorithm Rounds, Interactive Problems",
        "url": "https://csacademy.com",
    },
    {
        "id": "dmoj",
        "name": "DMOJ",
        "code": "DMOJ",
        "icon": "🦉",
        "type": "Live API & Feed",
        "formats": "Monthly Contests, CCC Prep, Canadian Olympiad",
        "url": "https://dmoj.ca",
    },
    {
        "id": "projecteuler",
        "name": "Project Euler",
        "code": "PE",
        "icon": "📐",
        "type": "Release Schedule",
        "formats": "Mathematical / Algorithmic Challenges",
        "url": "https://projecteuler.net",
    },
    {
        "id": "google",
        "name": "Google Competitions",
        "code": "GK",
        "icon": "🌐",
        "type": "Archive & Special",
        "formats": "Code Jam, Kick Start, Hash Code Archives",
        "url": "https://codingcompetitions.withgoogle.com",
    },
]


def get_console() -> Optional[Console]:
    """Return a Rich Console instance if rich is available."""
    if HAS_RICH:
        return Console()
    return None


def print_banner(console: Optional[Console] = None) -> None:
    """Display ASCII banner with modern terminal colors."""
    if console:
        banner_text = Text(BANNER_ART, style="bold cyan")
        tagline_text = Text(TAGLINE, style="bold bright_white on dark_blue")
        panel = Panel(
            Align.center(Text.assemble(banner_text, "\n", tagline_text)),
            box=ROUNDED,
            border_style="cyan",
            padding=(0, 2),
        )
        console.print(panel)
    else:
        print(BANNER_ART)
        print(f"  {TAGLINE}\n")


def format_countdown(starts_in_str: str) -> str:
    """Format starts-in string with ANSI or Rich color hints."""
    if "Ended" in starts_in_str:
        return f"[dim]{starts_in_str}[/dim]" if HAS_RICH else starts_in_str
    if "Running" in starts_in_str:
        return f"[bold green]{starts_in_str}[/bold green]" if HAS_RICH else starts_in_str
    if "< 1m" in starts_in_str or "Starting" in starts_in_str:
        return f"[bold red]{starts_in_str}[/bold red]" if HAS_RICH else starts_in_str
    if "m" in starts_in_str and "d" not in starts_in_str and "h" not in starts_in_str:
        return f"[bold yellow]{starts_in_str}[/bold yellow]" if HAS_RICH else starts_in_str
    return f"[cyan]{starts_in_str}[/cyan]" if HAS_RICH else starts_in_str


def _filter_by_platforms(contests: List[Contest], platform_filter: Optional[str]) -> List[Contest]:
    """Filter list of contests by comma-separated platforms."""
    if not platform_filter:
        return contests
    codes = {p.strip().lower() for p in platform_filter.split(",") if p.strip()}
    return [
        c
        for c in contests
        if c.platform.id.lower() in codes or c.platform.short_code.lower() in codes
    ]


def handle_list(args: argparse.Namespace, console: Optional[Console]) -> int:
    """Handle 'algoradar list' command."""
    storage = Storage()
    limit = args.limit if args.limit and args.limit > 0 else 15
    platform_filter = args.platform

    # Fetch contests
    if args.all:
        contests = storage.get_upcoming(limit=None) + storage.get_history(limit=50)
    else:
        contests = storage.get_upcoming(limit=None)

    # Filter by platform
    contests = _filter_by_platforms(contests, platform_filter)

    # Filter by status if requested
    if getattr(args, "status", None):
        status_filter = str(args.status).upper()
        contests = [c for c in contests if str(c.status).upper() == status_filter]

    # Filter favorites if requested
    if getattr(args, "favorites", False):
        contests = [c for c in contests if c.is_favorite]

    total_matched = len(contests)
    contests = contests[:limit]

    if not contests:
        if console:
            console.print("\n[yellow]No contests found matching criteria.[/yellow]")
            console.print(
                "[dim]Tip: Run '[bold cyan]algoradar sync[/bold cyan]' to fetch live contests from Codeforces, LeetCode, AtCoder, CodeChef, and HackerRank.[/dim]\n"
            )
        else:
            print("No contests found matching criteria.")
            print("Tip: Run 'algoradar sync' to fetch live contests.")
        return 0

    if console:
        table = Table(
            title="⚡ Upcoming & Active Competitive Programming Contests",
            box=ROUNDED,
            header_style="bold bright_cyan",
            title_style="bold white",
            show_lines=False,
            row_styles=["none", "dim"],
        )

        table.add_column("★", justify="center", style="yellow", width=3)
        table.add_column("Platform", justify="left", style="bold", width=14)
        table.add_column("Contest Name", justify="left", style="white", min_width=25)
        table.add_column("Start Time (UTC)", justify="center", style="cyan", width=18)
        table.add_column("Duration", justify="right", style="green", width=10)
        table.add_column("Starts In / Status", justify="left", width=22)
        table.add_column("URL", justify="left", style="dim underline", min_width=20)

        for c in contests:
            fav_icon = "★" if c.is_favorite else ""
            plat_color = PLATFORM_COLORS.get(c.platform.id.lower(), "white")
            plat_display = f"[{plat_color}]{c.platform.icon} {c.platform.name}[/{plat_color}]"

            # Truncate overly long contest names cleanly
            name_display = c.name if len(c.name) <= 46 else c.name[:43] + "..."

            utc_start = c.start_time.strftime("%b %d, %H:%M UTC")
            starts_in = format_countdown(c.starts_in_str())
            duration = c.duration_str()
            url_display = c.url

            table.add_row(
                fav_icon,
                plat_display,
                name_display,
                utc_start,
                duration,
                starts_in,
                url_display,
            )

        console.print(table)
        filter_str = f" [filter: {platform_filter}]" if platform_filter else ""
        console.print(
            f"[dim]Showing {len(contests)} of {total_matched} contests{filter_str}. Use '[bold cyan]algoradar export[/bold cyan]' to export to Google/Apple Calendar.[/dim]\n"
        )
    else:
        print(f"\nUpcoming Contests (Showing {len(contests)} of {total_matched}):")
        print("-" * 90)
        print(
            f"{'Platform':<15} {'Name':<35} {'Start (UTC)':<18} {'Duration':<10} {'Starts In':<15}"
        )
        print("-" * 90)
        for c in contests:
            name = c.name[:32] + "..." if len(c.name) > 35 else c.name
            print(
                f"{c.platform.name:<15} {name:<35} {c.start_time.strftime('%Y-%m-%d %H:%M'):<18} {c.duration_str():<10} {c.starts_in_str():<15}"
            )
        print("-" * 90 + "\n")

    return 0


def handle_now(args: argparse.Namespace, console: Optional[Console]) -> int:
    """Handle 'algoradar now' command."""
    storage = Storage()
    running_contests = storage.get_running()

    # Also double check in upcoming in case time crossed into running
    now_utc = datetime.now(timezone.utc)
    for c in storage.get_upcoming(limit=30):
        if c.start_time <= now_utc <= c.end_time and all(r.id != c.id for r in running_contests):
            c.status = ContestStatus.RUNNING
            running_contests.append(c)

    if not running_contests:
        if console:
            panel = Panel(
                Align.center(
                    Text.from_markup(
                        "[bold green]No contests currently running right now![/bold green]\n"
                        "[dim]Check '[bold cyan]algoradar list[/bold cyan]' to see upcoming rounds or "
                        "'[bold cyan]algoradar sync[/bold cyan]' to refresh live radar.[/dim]"
                    )
                ),
                box=ROUNDED,
                border_style="green",
                padding=(1, 2),
            )
            console.print(panel)
        else:
            print("\nNo contests currently running right now!")
            print("Run 'algoradar list' to see upcoming rounds.\n")
        return 0

    if console:
        table = Table(
            title="🔴 CURRENTLY RUNNING CONTESTS (ACTIVE RADAR)",
            box=HEAVY_EDGE,
            header_style="bold bright_red",
            title_style="bold bright_white on red",
        )

        table.add_column("Platform", justify="left", style="bold", width=15)
        table.add_column("Contest Name", justify="left", style="white", min_width=25)
        table.add_column("Started At (UTC)", justify="center", style="cyan", width=18)
        table.add_column("Time Remaining", justify="left", style="bold yellow", width=22)
        table.add_column("Contest Link", justify="left", style="dim underline", min_width=25)

        for c in running_contests:
            plat_color = PLATFORM_COLORS.get(c.platform.id.lower(), "white")
            plat_display = f"[{plat_color}]{c.platform.icon} {c.platform.name}[/{plat_color}]"
            rem = c.starts_in_str(now_utc)
            start_str = c.start_time.strftime("%b %d, %H:%M UTC")

            table.add_row(
                plat_display,
                c.name,
                start_str,
                f"[bold yellow]{rem}[/bold yellow]",
                c.url,
            )

        console.print(table)
        console.print(
            f"[bold green]⚡ {len(running_contests)} live contest(s) in progress. Good luck & high rating![/bold green]\n"
        )
    else:
        print(f"\n--- Currently Running Contests ({len(running_contests)}) ---")
        for c in running_contests:
            print(f"- [{c.platform.name}] {c.name}")
            print(f"  URL: {c.url}")
            print(f"  Status: {c.starts_in_str(now_utc)}\n")

    return 0


def handle_sync(args: argparse.Namespace, console: Optional[Console]) -> int:
    """Handle 'algoradar sync' command."""
    platform_filter = args.platform.split(",") if getattr(args, "platform", None) else None
    timeout = args.timeout if getattr(args, "timeout", None) else 15

    if console:
        console.print(
            Panel(
                Text.from_markup(
                    f"[bold cyan]⚡ AlgoRadar Sync Engine[/bold cyan]\n"
                    f"[dim]Connecting to Codeforces, LeetCode, AtCoder, CodeChef, and HackerRank APIs...[/dim]"
                ),
                box=ROUNDED,
                border_style="cyan",
            )
        )

    aggregator = Aggregator(timeout=timeout)

    # Perform concurrent sync
    start_time = datetime.now()
    fetched_contests = aggregator.fetch_all(
        platform_ids=platform_filter,
        include_finished=False,
    )
    elapsed = (datetime.now() - start_time).total_seconds()

    # Save to SQLite
    storage = Storage()
    saved_count = storage.save_contests(fetched_contests)

    # Report results by platform
    if console:
        table = Table(
            title="Radar Sync Results",
            box=SIMPLE,
            header_style="bold bright_white",
        )
        table.add_column("Platform", justify="left", style="bold")
        table.add_column("Status", justify="center")
        table.add_column("Contests Retrieved", justify="right", style="cyan")

        for ad in aggregator.adapters:
            pid = ad.platform.id
            if platform_filter and pid not in [p.lower() for p in platform_filter]:
                continue
            res = aggregator.last_results.get(pid, [])
            err = aggregator.last_errors.get(pid)

            plat_color = PLATFORM_COLORS.get(pid, "white")
            plat_label = f"[{plat_color}]{ad.platform.icon} {ad.platform.name}[/{plat_color}]"

            if err:
                status_label = "[red]✖ Warning (Fallback Used)[/red]"
            elif res:
                status_label = "[green]✔ Success[/green]"
            else:
                status_label = "[yellow]! 0 Found[/yellow]"

            table.add_row(plat_label, status_label, str(len(res)))

        console.print(table)
        console.print(
            f"[bold green]✔ Sync completed in {elapsed:.2f}s! {saved_count} contests cached in SQLite.[/bold green]"
        )
        console.print("[dim]Run '[bold cyan]algoradar list[/bold cyan]' to view updated radar.[/dim]\n")
    else:
        print(f"Sync completed in {elapsed:.2f}s.")
        print(f"Total contests cached: {saved_count}")
        for ad in aggregator.adapters:
            pid = ad.platform.id
            res = aggregator.last_results.get(pid, [])
            print(f"- {ad.platform.name}: {len(res)} contests")

    return 0


def handle_export(args: argparse.Namespace, console: Optional[Console]) -> int:
    """Handle 'algoradar export' command."""
    storage = Storage()
    platform_filter = args.platform
    fmt = (args.format or "ics").lower().strip()
    output_path = args.output or ("contests.ics" if fmt == "ics" else "contests.json")
    alarm_minutes = args.alarm if getattr(args, "alarm", None) is not None else 15

    contests = storage.get_upcoming(limit=None)
    if getattr(args, "running", True):
        for r in storage.get_running():
            if all(c.id != r.id for c in contests):
                contests.append(r)

    contests = _filter_by_platforms(contests, platform_filter)

    if not contests:
        msg = "No contests available to export. Run 'algoradar sync' first!"
        if console:
            console.print(f"[yellow]{msg}[/yellow]")
        else:
            print(msg)
        return 1

    out_file = Path(output_path).resolve()

    if fmt == "ics":
        written_path = export_ics(
            contests=contests,
            output_path=out_file,
            alarm_minutes=alarm_minutes,
        )
    elif fmt == "json":
        data = [c.to_dict() for c in contests]
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        written_path = out_file
    else:
        if console:
            console.print(f"[red]Error: Unsupported export format '{fmt}'. Use 'ics' or 'json'.[/red]")
        else:
            print(f"Error: Unsupported export format '{fmt}'. Use 'ics' or 'json'.")
        return 1

    size_kb = written_path.stat().st_size / 1024

    if console:
        panel = Panel(
            Text.from_markup(
                f"[bold green]✔ Export Successful![/bold green]\n\n"
                f"• [bold]Format:[/bold] {fmt.upper()}\n"
                f"• [bold]Events Exported:[/bold] {len(contests)} contests\n"
                f"• [bold]Pre-Contest Alarm:[/bold] {alarm_minutes} minutes before start\n"
                f"• [bold]File Destination:[/bold] [cyan]{written_path}[/cyan] ({size_kb:.1f} KB)\n\n"
                f"[bold bright_white]How to import into your calendar:[/bold bright_white]\n"
                f"  1. [bold]Google Calendar:[/bold] Settings -> Import & Export -> Select '{written_path.name}'\n"
                f"  2. [bold]Apple Calendar / Outlook:[/bold] Double-click the file to subscribe or import\n"
            ),
            box=ROUNDED,
            border_style="green",
            title="📅 Calendar Export",
        )
        console.print(panel)
    else:
        print(f"Exported {len(contests)} contests to {written_path} ({size_kb:.1f} KB)")
        print(f"Format: {fmt.upper()}, Alarms: {alarm_minutes}m before start")

    return 0


def handle_platforms(args: argparse.Namespace, console: Optional[Console]) -> int:
    """Handle 'algoradar platforms' command."""
    if console:
        table = Table(
            title="🌐 Supported Competitive Programming Platforms (10+ Indexed)",
            box=ROUNDED,
            header_style="bold bright_cyan",
            title_style="bold white",
        )

        table.add_column("Icon", justify="center", width=4)
        table.add_column("Platform Name", justify="left", style="bold", width=18)
        table.add_column("Code", justify="center", style="cyan", width=6)
        table.add_column("Integration Type", justify="left", style="green", width=18)
        table.add_column("Supported Formats", justify="left", style="white", min_width=30)
        table.add_column("Official Website", justify="left", style="dim underline", min_width=24)

        for p in SUPPORTED_PLATFORMS_CATALOG:
            plat_color = PLATFORM_COLORS.get(p["id"], "white")
            table.add_row(
                p["icon"],
                f"[{plat_color}]{p['name']}[/{plat_color}]",
                p["code"],
                p["type"],
                p["formats"],
                p["url"],
            )

        console.print(table)
        console.print(
            "[dim]Tip: Filter by platform short code in any command, e.g. '[bold cyan]algoradar list -p CF,LC[/bold cyan]'.[/dim]\n"
        )
    else:
        print("\n--- Supported CP Platforms (10+ Indexed) ---")
        for p in SUPPORTED_PLATFORMS_CATALOG:
            print(f"{p['icon']} {p['name']} ({p['code']}) - {p['type']}")
            print(f"   Formats: {p['formats']}")
            print(f"   Website: {p['url']}\n")

    return 0


def handle_stats(args: argparse.Namespace, console: Optional[Console]) -> int:
    """Handle 'algoradar stats' command."""
    storage = Storage()
    db_path = storage.db_path

    db_exists = db_path.exists()
    db_size_kb = (db_path.stat().st_size / 1024) if db_exists else 0.0

    all_upcoming = storage.get_upcoming(limit=None)
    all_running = storage.get_running()
    all_history = storage.get_history(limit=500)
    favorites = storage.get_favorites()

    total_contests = len(all_upcoming) + len(all_running) + len(all_history)

    # Count by platform
    platform_counts: dict[str, int] = {}
    for c in all_upcoming + all_running + all_history:
        p_name = c.platform.name
        platform_counts[p_name] = platform_counts.get(p_name, 0) + 1

    next_contest = all_upcoming[0] if all_upcoming else None

    if console:
        # Build diagnostic panel
        grid = Table.grid(expand=True, padding=(0, 2))
        grid.add_column(style="bold cyan", width=22)
        grid.add_column(style="white")

        grid.add_row("Database Path:", str(db_path))
        grid.add_row("Database File Size:", f"{db_size_kb:.2f} KB (SQLite WAL mode)")
        grid.add_row("Total Contests Tracked:", f"[bold white]{total_contests}[/bold white]")
        grid.add_row("• Upcoming Contests:", f"[cyan]{len(all_upcoming)}[/cyan]")
        grid.add_row("• Running Contests:", f"[bold green]{len(all_running)}[/bold green]")
        grid.add_row("• Finished / History:", f"[dim]{len(all_history)}[/dim]")
        grid.add_row("• Bookmarked Favorites:", f"[yellow]★ {len(favorites)}[/yellow]")

        if next_contest:
            grid.add_row(
                "Next Contest:",
                f"[{PLATFORM_COLORS.get(next_contest.platform.id, 'white')}]{next_contest.platform.icon} {next_contest.name}[/] ({next_contest.starts_in_str()})",
            )
        else:
            grid.add_row("Next Contest:", "[dim]None scheduled (run 'algoradar sync')[/dim]")

        # Platform distribution
        plat_breakdown = ", ".join(f"{k}: [bold]{v}[/bold]" for k, v in sorted(platform_counts.items()))
        grid.add_row("Platform Distribution:", plat_breakdown or "[dim]None[/dim]")

        panel = Panel(
            grid,
            box=ROUNDED,
            border_style="cyan",
            title="📊 AlgoRadar Workstation Diagnostics & Storage Stats",
            padding=(1, 2),
        )
        console.print(panel)
        console.print()
    else:
        print("\n--- AlgoRadar Workstation Stats ---")
        print(f"Database Path: {db_path}")
        print(f"Database Size: {db_size_kb:.2f} KB")
        print(f"Total Contests Tracked: {total_contests}")
        print(f"  Upcoming: {len(all_upcoming)}")
        print(f"  Running:  {len(all_running)}")
        print(f"  History:  {len(all_history)}")
        print(f"  Favorites: {len(favorites)}")
        if next_contest:
            print(f"Next Contest: [{next_contest.platform.name}] {next_contest.name} ({next_contest.starts_in_str()})")
        print(f"Platform Breakdown: {platform_counts}\n")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="algoradar",
        description="AlgoRadar - Terminal Competitive Programming Contest Radar & Workstation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
        "  algoradar list --platform CF,LC --limit 10\n"
        "  algoradar now\n"
        "  algoradar sync\n"
        "  algoradar export --format ics --output calendar.ics\n"
        "  algoradar platforms\n"
        "  algoradar stats\n",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="AlgoRadar 1.0.0",
        help="Show AlgoRadar version and exit",
    )
    parser.add_argument(
        "--banner",
        action="store_true",
        help="Print ASCII art workstation banner",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list subcommand
    list_parser = subparsers.add_parser("list", help="List upcoming competitive programming contests")
    list_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        default=None,
        help="Filter by platform codes or names (e.g. CF,LC or codeforces,leetcode)",
    )
    list_parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=15,
        help="Maximum number of contests to display (default: 15)",
    )
    list_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include past / finished contests in the listing",
    )
    list_parser.add_argument(
        "--status",
        type=str,
        choices=["UPCOMING", "RUNNING", "FINISHED"],
        default=None,
        help="Filter by contest lifecycle status",
    )
    list_parser.add_argument(
        "--favorites",
        "--fav",
        action="store_true",
        help="Show only bookmarked favorite contests",
    )

    # now subcommand
    subparsers.add_parser("now", help="Display currently running / active contests")

    # sync subcommand
    sync_parser = subparsers.add_parser(
        "sync", help="Fetch live contests from all platform APIs and cache in SQLite"
    )
    sync_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        default=None,
        help="Limit sync to specific platform(s) (e.g. CF,LC)",
    )
    sync_parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=15,
        help="Network request timeout in seconds (default: 15)",
    )

    # export subcommand
    export_parser = subparsers.add_parser(
        "export", help="Export tracked contests to standard iCalendar (.ics) or JSON"
    )
    export_parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["ics", "json"],
        default="ics",
        help="Export format: 'ics' (default) or 'json'",
    )
    export_parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output destination file path (default: contests.ics or contests.json)",
    )
    export_parser.add_argument(
        "-p",
        "--platform",
        type=str,
        default=None,
        help="Filter export by platform(s) (e.g. CF,LC)",
    )
    export_parser.add_argument(
        "-a",
        "--alarm",
        type=int,
        default=15,
        help="Minutes before contest start for reminder alarm (default: 15)",
    )
    export_parser.add_argument(
        "--no-running",
        dest="running",
        action="store_false",
        help="Exclude currently running contests from export",
    )

    # platforms subcommand
    subparsers.add_parser("platforms", help="Display comprehensive list of 10+ supported platforms")

    # stats subcommand
    subparsers.add_parser("stats", help="Display workstation database and tracking statistics")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entrypoint for AlgoRadar workstation."""
    parser = build_parser()
    args = parser.parse_args(argv)
    console = get_console()

    # If no command provided, print banner and run default list
    if args.command is None:
        print_banner(console)
        # Default to showing upcoming contests
        args.limit = 10
        args.platform = None
        args.all = False
        args.status = None
        args.favorites = False
        return handle_list(args, console)

    if args.banner:
        print_banner(console)

    if args.command == "list":
        return handle_list(args, console)
    elif args.command == "now":
        return handle_now(args, console)
    elif args.command == "sync":
        return handle_sync(args, console)
    elif args.command == "export":
        return handle_export(args, console)
    elif args.command == "platforms":
        return handle_platforms(args, console)
    elif args.command == "stats":
        return handle_stats(args, console)

    return 0


if __name__ == "__main__":
    sys.exit(main())

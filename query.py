"""
Query CLI — Command-line interface for querying drone security events.

Supports:
  --object "truck"           : Search by object type (SQLite)
  --time "after 22:00"       : Search by time window (SQLite)
  --search "suspicious ..."  : Semantic search (ChromaDB)
  --alerts                   : Show all triggered alerts
  --summary                  : Show session statistics
  --location "Main Gate"     : Search by location
  --suspicious               : Show all suspicious events
"""

import sys
import os
import argparse

os.environ["PYTHONIOENCODING"] = "utf-8"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from config import ensure_data_dir

console = Console(force_terminal=True)


def show_object_results(store: SQLiteStore, object_type: str):
    """Search frames by object type."""
    results = store.query_by_object(object_type)

    if not results:
        console.print(f"[yellow]No frames found containing '{object_type}'[/yellow]")
        return

    table = Table(
        title=f"Frames containing '{object_type}' ({len(results)} results)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Frame", justify="center", style="bold")
    table.add_column("Time", style="cyan")
    table.add_column("Location")
    table.add_column("Event Type")
    table.add_column("Risk", justify="center")
    table.add_column("Description", max_width=50)

    for r in results:
        risk = r.get("risk_level", "low").upper()
        risk_color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(risk, "white")
        table.add_row(
            str(r["frame_id"]),
            r["timestamp"],
            r["location"],
            r.get("event_type", "-"),
            f"[{risk_color}]{risk}[/{risk_color}]",
            (r.get("analysis_summary") or r.get("raw_description", "-"))[:50],
        )

    console.print(table)


def show_time_results(store: SQLiteStore, time_query: str):
    """Search frames by time range."""
    # Parse time query
    time_query = time_query.lower().strip()

    if "after" in time_query:
        # Extract time after "after"
        time_part = time_query.replace("after", "").strip()
        start_time = time_part
        end_time = "23:59"
    elif "before" in time_query:
        time_part = time_query.replace("before", "").strip()
        start_time = "00:00"
        end_time = time_part
    elif "-" in time_query or "to" in time_query:
        parts = time_query.replace("to", "-").split("-")
        start_time = parts[0].strip()
        end_time = parts[1].strip()
    else:
        # Assume it's a specific time, show +/- 30 min
        start_time = time_query
        end_time = time_query
        console.print(f"[dim]Showing events at {time_query}[/dim]")

    results = store.query_by_time_range(start_time, end_time)

    if not results:
        console.print(f"[yellow]No frames found in time range {start_time} - {end_time}[/yellow]")
        return

    table = Table(
        title=f"Frames from {start_time} to {end_time} ({len(results)} results)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Frame", justify="center", style="bold")
    table.add_column("Time", style="cyan")
    table.add_column("Location")
    table.add_column("Event Type")
    table.add_column("Risk", justify="center")
    table.add_column("Description", max_width=50)

    for r in results:
        risk = r.get("risk_level", "low").upper()
        risk_color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(risk, "white")
        table.add_row(
            str(r["frame_id"]),
            r["timestamp"],
            r["location"],
            r.get("event_type", "-"),
            f"[{risk_color}]{risk}[/{risk_color}]",
            (r.get("analysis_summary") or r.get("raw_description", "-"))[:50],
        )

    console.print(table)


def show_semantic_search(chroma_store: ChromaStore, query: str):
    """Semantic search using ChromaDB."""
    results = chroma_store.semantic_search(query, top_k=10)

    if not results:
        console.print(f"[yellow]No semantic matches found for '{query}'[/yellow]")
        return

    table = Table(
        title=f"Semantic Search: '{query}' ({len(results)} results)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Frame", justify="center", style="bold")
    table.add_column("Time", style="cyan")
    table.add_column("Location")
    table.add_column("Relevance", justify="center")
    table.add_column("Description", max_width=60)

    for r in results:
        similarity = 1 - r.get("distance", 0)
        sim_color = "green" if similarity > 0.7 else "yellow" if similarity > 0.4 else "red"
        table.add_row(
            str(r.get("frame_id", "?")),
            r.get("timestamp", "-"),
            r.get("location", "-"),
            f"[{sim_color}]{similarity:.1%}[/{sim_color}]",
            r.get("raw_description", r.get("document", "-"))[:60],
        )

    console.print(table)


def show_alerts(store: SQLiteStore):
    """Show all triggered alerts."""
    alerts = store.get_all_alerts()

    if not alerts:
        console.print("[green]No alerts were triggered during this session.[/green]")
        return

    table = Table(
        title=f"Alert Log ({len(alerts)} total alerts)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red",
    )
    table.add_column("ID", justify="center", style="bold")
    table.add_column("Frame", justify="center")
    table.add_column("Time", style="cyan")
    table.add_column("Severity", justify="center")
    table.add_column("Rule")
    table.add_column("Location")
    table.add_column("Message", max_width=50)

    for alert in alerts:
        sev = alert["severity"]
        color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(sev, "white")
        table.add_row(
            str(alert["alert_id"]),
            str(alert.get("frame_id", "-")),
            alert["timestamp"],
            f"[{color}]{sev}[/{color}]",
            alert.get("rule_name", "-"),
            alert.get("location", "-"),
            alert["message"][:50],
        )

    console.print(table)


def show_summary(store: SQLiteStore):
    """Show session statistics."""
    stats = store.get_session_stats()

    console.print(Panel(
        f"""[bold]Session Statistics[/bold]

Total Frames: {stats['total_frames']}
Suspicious Events: [red]{stats['suspicious_frames']}[/red]
Total Alerts: [yellow]{stats['total_alerts']}[/yellow]

[bold]Alerts by Severity:[/bold]
{chr(10).join(f"  [{sev}]: {count}" for sev, count in sorted(stats.get('alerts_by_severity', {}).items()))}""",
        title="[bold cyan]Session Summary[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
    ))


def show_suspicious(store: SQLiteStore):
    """Show all suspicious events."""
    results = store.query_suspicious_frames()

    if not results:
        console.print("[green]No suspicious events recorded.[/green]")
        return

    table = Table(
        title=f"Suspicious Events ({len(results)} total)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red",
    )
    table.add_column("Frame", justify="center", style="bold")
    table.add_column("Time", style="cyan")
    table.add_column("Location")
    table.add_column("Event Type")
    table.add_column("Risk", justify="center")
    table.add_column("Description", max_width=50)

    for r in results:
        risk = r.get("risk_level", "").upper()
        risk_color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(risk, "white")
        table.add_row(
            str(r["frame_id"]),
            r["timestamp"],
            r["location"],
            r.get("event_type", "-"),
            f"[{risk_color}]{risk}[/{risk_color}]",
            (r.get("analysis_summary") or r.get("raw_description", "-"))[:50],
        )

    console.print(table)


def show_location_results(store: SQLiteStore, location: str):
    """Search frames by location."""
    results = store.query_by_location(location)

    if not results:
        console.print(f"[yellow]No frames found at '{location}'[/yellow]")
        return

    table = Table(
        title=f"Events at '{location}' ({len(results)} results)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Frame", justify="center", style="bold")
    table.add_column("Time", style="cyan")
    table.add_column("Location")
    table.add_column("Event Type")
    table.add_column("Risk", justify="center")
    table.add_column("Description", max_width=50)

    for r in results:
        risk = r.get("risk_level", "").upper()
        risk_color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(risk, "white")
        table.add_row(
            str(r["frame_id"]),
            r["timestamp"],
            r["location"],
            r.get("event_type", "-"),
            f"[{risk_color}]{risk}[/{risk_color}]",
            (r.get("analysis_summary") or r.get("raw_description", "-"))[:50],
        )

    console.print(table)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Drone Security Event Query Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query.py --object "truck"
  python query.py --time "after 22:00"
  python query.py --search "suspicious nighttime activity"
  python query.py --alerts
  python query.py --summary
  python query.py --suspicious
  python query.py --location "Main Gate"
        """
    )

    parser.add_argument("--object", "-o", type=str, help="Search by object type (e.g., 'truck', 'person')")
    parser.add_argument("--time", "-t", type=str, help="Search by time (e.g., 'after 22:00', '06:00-12:00')")
    parser.add_argument("--search", "-s", type=str, help="Semantic search query (ChromaDB)")
    parser.add_argument("--alerts", "-a", action="store_true", help="Show all triggered alerts")
    parser.add_argument("--summary", action="store_true", help="Show session summary statistics")
    parser.add_argument("--suspicious", action="store_true", help="Show all suspicious events")
    parser.add_argument("--location", "-l", type=str, help="Search by location")

    args = parser.parse_args()

    # Check if any argument was provided
    if not any([args.object, args.time, args.search, args.alerts, args.summary,
                args.suspicious, args.location]):
        parser.print_help()
        return

    ensure_data_dir()

    console.print(Panel(
        "[bold]Drone Security Event Query System[/bold]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
    ))

    # Initialize stores
    sqlite_store = SQLiteStore()

    if args.object:
        show_object_results(sqlite_store, args.object)

    if args.time:
        show_time_results(sqlite_store, args.time)

    if args.search:
        chroma_store = ChromaStore()
        show_semantic_search(chroma_store, args.search)

    if args.alerts:
        show_alerts(sqlite_store)

    if args.summary:
        show_summary(sqlite_store)

    if args.suspicious:
        show_suspicious(sqlite_store)

    if args.location:
        show_location_results(sqlite_store, args.location)

    sqlite_store.close()


if __name__ == "__main__":
    main()

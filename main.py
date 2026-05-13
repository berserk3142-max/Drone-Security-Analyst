"""
Drone Security Analyst Agent — Main Pipeline

Processes all simulated drone surveillance frames through:
1. Telemetry generation
2. VLM frame analysis (Gemini)
3. LangChain agent reasoning (log, alert, pattern detection)
4. Dual indexing (SQLite + ChromaDB)

Produces a professional security monitoring console output.
"""

import sys
import time
import os

# Fix Windows encoding
os.environ["PYTHONIOENCODING"] = "utf-8"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from config import PROPERTY_NAME, DRONE_ID, ensure_data_dir
from simulators.frames import get_simulated_frames
from simulators.telemetry import TelemetrySimulator
from analysis.vlm_analyzer import analyze_frame
from agent.security_agent import SecurityAgent
from indexing.sqlite_store import SQLiteStore
from indexing.chroma_store import ChromaStore
from alerts.rules_engine import AlertManager

console = Console(force_terminal=True)


def print_header():
    """Print the monitoring session header."""
    header = Text()
    header.append("DRONE SECURITY ANALYST AGENT", style="bold white")
    header.append("\n")
    header.append("\n")
    header.append(f"Property: {PROPERTY_NAME}", style="cyan")
    header.append(f"  |  Drone: {DRONE_ID}", style="cyan")
    header.append(f"  |  Mode: Autonomous Patrol", style="cyan")

    console.print(Panel(
        header,
        title="[bold green]>> MONITORING SESSION STARTED[/bold green]",
        border_style="green",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    ))
    console.print()


def print_frame_result(frame: dict, analysis: dict, agent_result: dict, alerts: list):
    """Print the result of processing a single frame."""
    time_str = frame["time"]
    location = frame["location"]
    risk = analysis.get("risk_level", "low").upper()

    # Color based on risk
    risk_colors = {
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "red",
        "CRITICAL": "bold red",
    }
    risk_color = risk_colors.get(risk, "white")

    # Status icon
    if risk in ("CRITICAL", "HIGH"):
        icon = "[!!]"
    elif risk == "MEDIUM":
        icon = "[!]"
    else:
        icon = "[+]"

    # Main log line
    objects_str = ", ".join(analysis.get("objects", ["-"]))
    event_type = analysis.get("event_type", "unknown")
    description = analysis.get("description", "")

    console.print(
        f"  [{risk_color}][{time_str}][/{risk_color}] "
        f"{icon} "
        f"[bold]{event_type.upper()}[/bold] at [cyan]{location}[/cyan] - "
        f"{objects_str}"
    )

    if description:
        console.print(f"          > {description}", style="dim")

    # Print alerts
    for alert in alerts:
        sev = alert.get("severity", "")
        msg = alert.get("message", "")
        sev_color = risk_colors.get(sev, "white")
        console.print(f"         [bold {sev_color}]ALERT [{sev}]: {msg}[/bold {sev_color}]")

    console.print()


def print_session_summary(sqlite_store: SQLiteStore, alert_manager: AlertManager):
    """Print the end-of-session summary."""
    stats = sqlite_store.get_session_stats()
    all_alerts = sqlite_store.get_all_alerts()

    console.print()
    console.print(Panel(
        "[bold white]SESSION COMPLETE[/bold white]",
        title="[bold cyan]>> MONITORING SESSION ENDED[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
    ))

    # Stats table
    stats_table = Table(
        title="Session Statistics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    stats_table.add_column("Metric", style="bold")
    stats_table.add_column("Value", justify="right")

    stats_table.add_row("Total Frames Processed", str(stats["total_frames"]))
    stats_table.add_row("Suspicious Events", f"[red]{stats['suspicious_frames']}[/red]")
    stats_table.add_row("Total Alerts Fired", f"[yellow]{stats['total_alerts']}[/yellow]")

    for sev, count in sorted(stats.get("alerts_by_severity", {}).items()):
        color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(sev, "white")
        stats_table.add_row(f"  > {sev} Alerts", f"[{color}]{count}[/{color}]")

    console.print(stats_table)

    # Alert details
    if all_alerts:
        console.print()
        alert_table = Table(
            title="Alert Log",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold red",
        )
        alert_table.add_column("Time", style="cyan")
        alert_table.add_column("Severity", justify="center")
        alert_table.add_column("Location")
        alert_table.add_column("Message", max_width=60)

        for alert in all_alerts:
            sev = alert["severity"]
            color = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(sev, "white")
            alert_table.add_row(
                alert["timestamp"],
                f"[{color}]{sev}[/{color}]",
                alert.get("location", "-"),
                alert["message"][:60],
            )

        console.print(alert_table)


def main():
    """Run the main monitoring pipeline."""
    ensure_data_dir()

    # Initialize components
    sqlite_store = SQLiteStore()
    chroma_store = ChromaStore()
    alert_manager = AlertManager()
    telemetry_sim = TelemetrySimulator()

    # Clear previous session data
    sqlite_store.clear_all()
    try:
        chroma_store.clear_all()
    except Exception:
        pass

    # Initialize the LangChain agent
    console.print("[dim]Initializing AI Security Agent...[/dim]")
    agent = SecurityAgent(sqlite_store, chroma_store, alert_manager)
    console.print("[green]>> Agent initialized successfully[/green]\n")

    # Get simulated frames
    frames = get_simulated_frames()

    # Print header
    print_header()

    total_alerts = []

    # Process each frame
    for i, frame in enumerate(frames):
        frame_label = f"Frame {frame['frame_id']}/{len(frames)}"

        console.print(
            f"  [dim]--- {frame_label} ---[/dim]",
            style="dim",
        )

        # Step 1: Generate telemetry
        telemetry = telemetry_sim.get_telemetry(frame["time"], frame["location"])

        # Step 2: VLM frame analysis
        console.print(f"  [dim]  Analyzing frame with VLM...[/dim]")
        analysis = analyze_frame(frame["description"], telemetry)

        # Step 3: Agent processing
        console.print(f"  [dim]  Agent processing...[/dim]")
        agent_result = agent.process_frame(frame, analysis, telemetry)

        # Collect alerts for this frame
        frame_alerts = [a for a in alert_manager.fired_alerts
                       if a.get("frame_id") == frame["frame_id"]]
        total_alerts.extend(frame_alerts)

        # Step 4: Print results
        print_frame_result(frame, analysis, agent_result, frame_alerts)

        # Delay between frames to respect API rate limits (free tier: 15 RPM)
        if i < len(frames) - 1:
            time.sleep(4)

    # Print session summary
    print_session_summary(sqlite_store, alert_manager)

    # Generate agent summary
    console.print("\n[dim]Generating AI session summary...[/dim]")
    try:
        summary = agent.get_summary()
        console.print(Panel(
            summary,
            title="[bold cyan]AI Security Analyst Summary[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        ))
    except Exception as e:
        console.print(f"[yellow]Summary generation skipped: {e}[/yellow]")

    # Cleanup
    sqlite_store.close()
    console.print("\n[green]>> Session data saved to SQLite + ChromaDB[/green]")
    console.print("[green]>> Run 'python query.py --help' to query events[/green]")


if __name__ == "__main__":
    main()

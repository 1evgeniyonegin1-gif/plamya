#!/usr/bin/env python3
"""PLAMYA CLI - From ashes, autonomy."""

import os
import sys
import time
import json
import shutil
from pathlib import Path

VERSION = "0.1.0"
PLAMYA_HOME = Path.home() / ".plamya"

# ── Rich imports (graceful fallback) ─────────────────────────────

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    import pyfiglet
    HAS_FIGLET = True
except ImportError:
    HAS_FIGLET = False

console = Console() if HAS_RICH else None

# ── Fire gradient ────────────────────────────────────────────────

FIRE_COLORS = [
    "#3d0c02",  # deep ember
    "#6b1a0a",  # dark red
    "#a82812",  # crimson
    "#d4451a",  # red-orange
    "#e8611a",  # orange
    "#f28c28",  # bright orange
    "#f5b041",  # amber
    "#f9d342",  # gold
    "#fce94f",  # yellow
    "#fdf6e3",  # hot white
]


def gradient_text(text_str, colors=None):
    """Apply vertical fire gradient to multiline text."""
    if not HAS_RICH:
        return text_str
    if colors is None:
        colors = FIRE_COLORS

    lines = text_str.split("\n")
    rich_text = Text()
    n = len(lines)
    for i, line in enumerate(lines):
        # Map line index to color gradient
        idx = int(i / max(n - 1, 1) * (len(colors) - 1))
        rich_text.append(line + "\n", style=colors[idx])
    return rich_text


def get_banner():
    """Generate the PLAMYA figlet banner with fire gradient."""
    if HAS_FIGLET:
        raw = pyfiglet.figlet_format("PLAMYA", font="slant")
    else:
        raw = (
            "    ____  __    ___    __  ____  _____\n"
            "   / __ \\/ /   /   |  /  |/  /\\ \\/ /   |\n"
            "  / /_/ / /   / /| | / /|_/ /  \\  / /| |\n"
            " / ____/ /___/ ___ |/ /  / /   / / ___ |\n"
            "/_/   /_____/_/  |_/_/  /_/   /_/_/  |_|\n"
        )
    return raw.rstrip("\n")


# ── Status helpers ───────────────────────────────────────────────

def check_forge():
    """Gather system status."""
    checks = []

    # State directory
    if PLAMYA_HOME.exists():
        checks.append(("The Forge", str(PLAMYA_HOME), True))
    else:
        checks.append(("The Forge", "not initialized  [dim](plamya ignite)[/dim]", False))

    # Agents (embers)
    embers_dir = PLAMYA_HOME / "embers"
    if embers_dir.exists():
        agents = list(embers_dir.glob("*.json"))
        if agents:
            names = ", ".join(f"[cyan]{a.stem}[/cyan]" for a in agents)
            checks.append(("Agents", f"{len(agents)} ember(s): {names}", True))
        else:
            checks.append(("Agents", "[dim]no embers[/dim]", False))
    else:
        checks.append(("Agents", "[dim]no embers[/dim]", False))

    # Heartbeat
    status_file = PLAMYA_HOME / "shared" / "STATUS.md"
    if status_file.exists():
        ago = int(time.time() - status_file.stat().st_mtime)
        if ago < 60:
            age = f"{ago}s ago"
        elif ago < 3600:
            age = f"{ago // 60}m ago"
        else:
            age = f"{ago // 3600}h ago"
        checks.append(("Heartbeat", f"last pulse [green]{age}[/green]", True))
    else:
        checks.append(("Heartbeat", "[dim]no pulse[/dim]", False))

    # Secrets
    secrets_dir = PLAMYA_HOME / "secrets"
    if secrets_dir.exists():
        checks.append(("Secrets", "[green]Fernet encrypted[/green]", True))
    else:
        checks.append(("Secrets", "[dim]not configured[/dim]", False))

    # Claude CLI
    claude_path = shutil.which("claude") or shutil.which("claude.cmd")
    if claude_path:
        checks.append(("AI Engine", f"Claude CLI [dim]{claude_path}[/dim]", True))
    else:
        checks.append(("AI Engine", "[yellow]Claude CLI not found[/yellow] [dim](fallback: API)[/dim]", False))

    # Security guards
    guards = ["input_guard", "output_guard", "action_guard", "canary"]
    shared_dir = Path(__file__).parent / "shared"
    found = [g for g in guards if (shared_dir / (g + ".py")).exists()]
    if len(found) == 4:
        checks.append(("Security", "[green]4-layer defense active[/green]", True))
    else:
        checks.append(("Security", f"[yellow]{len(found)}/4 guards[/yellow]", False))

    return checks


# ── Commands (Rich version) ──────────────────────────────────────

def print_banner():
    """Print the fire-gradient banner."""
    if not HAS_RICH:
        print("\n" + get_banner())
        print('  "From ashes, autonomy."  v' + VERSION + "\n")
        return

    banner_text = gradient_text(get_banner())
    console.print()
    console.print(banner_text, justify="center")
    tagline = Text()
    tagline.append('"From ashes, autonomy."', style="dim italic")
    tagline.append(f"  v{VERSION}", style="dim")
    console.print(tagline, justify="center")
    console.print()


def cmd_status():
    """Show PLAMYA system status."""
    if not HAS_RICH:
        _cmd_status_plain()
        return

    checks = check_forge()

    table = Table(
        show_header=False,
        box=box.SIMPLE_HEAVY,
        border_style="bright_black",
        padding=(0, 2),
        expand=True,
    )
    table.add_column("icon", width=3, justify="center")
    table.add_column("label", width=12, style="bold")
    table.add_column("value")

    for label, value, ok in checks:
        icon = "[green]\u25cf[/green]" if ok else "[red]\u25cb[/red]"
        table.add_row(icon, label, value)

    panel = Panel(
        table,
        title="[bold bright_white]\u2593 The Forge[/bold bright_white]",
        subtitle=f"[dim]{PLAMYA_HOME}[/dim]",
        border_style="#e8611a",
        box=box.HEAVY,
        padding=(1, 2),
    )
    console.print(panel)


def cmd_help():
    """Show available commands."""
    if not HAS_RICH:
        _cmd_help_plain()
        return

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 3),
    )
    table.add_column("cmd", style="bold #f28c28", width=12)
    table.add_column("desc", style="white")

    cmds = [
        ("ignite",  "Initialize The Forge, create ~/.plamya/"),
        ("status",  "Show agent status and system health"),
        ("spark",   "Create a new agent (ember + state dir)"),
        ("rise",    "Deploy (project-specific)"),
        ("ash",     "Cleanup \u2014 sweep the ashes"),
        ("version", "Show version"),
        ("help",    "Show this help"),
    ]
    for name, desc in cmds:
        table.add_row(name, desc)

    panel = Panel(
        table,
        title="[bold bright_white]Commands[/bold bright_white]",
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)


def cmd_ignite():
    """Initialize The Forge."""
    if HAS_RICH:
        console.print()
        console.print("  [bold #f28c28]\u2592\u2592\u2592[/] [bold]Igniting The Forge...[/]")
        console.print()
    else:
        print("\n  >>> Igniting The Forge...\n")

    dirs = [
        PLAMYA_HOME,
        PLAMYA_HOME / "embers",
        PLAMYA_HOME / "shared",
        PLAMYA_HOME / "secrets",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        if HAS_RICH:
            console.print(f"  [green]+[/green] {d}")
        else:
            print(f"  + {d}")

    if sys.platform != "win32":
        os.chmod(PLAMYA_HOME / "secrets", 0o700)

    sf = PLAMYA_HOME / "shared" / "STATUS.md"
    if not sf.exists():
        sf.write_text("# PLAMYA Agent Status\n\nNo agents running yet.\n", encoding="utf-8")
        if HAS_RICH:
            console.print(f"  [green]+[/green] {sf}")
        else:
            print(f"  + {sf}")

    ib = PLAMYA_HOME / "shared" / "INBOX.md"
    if not ib.exists():
        ib.write_text("# PLAMYA Inbox\n\nNo messages.\n", encoding="utf-8")
        if HAS_RICH:
            console.print(f"  [green]+[/green] {ib}")
        else:
            print(f"  + {ib}")

    if HAS_RICH:
        console.print()
        console.print("  [bold green]The Forge is lit.[/] [dim]Add agent configs to embers/[/]")
        console.print("  [dim]See: examples/chappie/ for how to create an agent[/]")
        console.print()
    else:
        print("\n  The Forge is lit. Add agent configs to embers/\n")


def cmd_spark():
    """Create a new agent."""
    if HAS_RICH:
        console.print()
        name = console.input("  [bold #f28c28]?[/] Agent name: ").strip().lower()
    else:
        print()
        name = input("  ? Agent name: ").strip().lower()

    if not name:
        msg = "Name required"
        console.print(f"  [red]![/] {msg}") if HAS_RICH else print(f"  ! {msg}")
        return
    if not name.isidentifier():
        msg = "Name must be a valid Python identifier"
        console.print(f"  [red]![/] {msg}") if HAS_RICH else print(f"  ! {msg}")
        return

    embers_dir = PLAMYA_HOME / "embers"
    embers_dir.mkdir(parents=True, exist_ok=True)
    cf = embers_dir / (name + ".json")
    if cf.exists():
        msg = f"Ember already exists: {cf}"
        console.print(f"  [yellow]![/] {msg}") if HAS_RICH else print(f"  ! {msg}")
        return

    config = {
        "name": name,
        "description": name + " agent",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "allowed_actions": ["get_status"],
    }
    cf.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    ad = PLAMYA_HOME / name
    ad.mkdir(parents=True, exist_ok=True)

    if HAS_RICH:
        console.print(f"  [green]+[/green] Ember: {cf}")
        console.print(f"  [green]+[/green] State: {ad}")
        console.print()
        console.print("  [bold green]Spark created.[/] [dim]The ember glows, waiting to be fanned.[/]")
        console.print()
    else:
        print(f"  + Ember: {cf}")
        print(f"  + State: {ad}")
        print("\n  Spark created.\n")


def cmd_ash():
    """Cleanup state."""
    if not PLAMYA_HOME.exists():
        msg = "Nothing to clean. The Forge is cold."
        console.print(f"\n  [dim]{msg}[/]") if HAS_RICH else print(f"\n  {msg}")
        return

    try:
        if HAS_RICH:
            console.print()
            ans = console.input(f"  [bold red]?[/] Sweep the ashes from [bold]{PLAMYA_HOME}[/]? [dim]\\[y/N][/] ").strip().lower()
        else:
            ans = input(f"\n  ? Sweep ashes from {PLAMYA_HOME}? [y/N] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    if ans != "y":
        msg = "Cancelled."
        console.print(f"  [dim]{msg}[/]") if HAS_RICH else print(f"  {msg}")
        return

    import shutil as sh
    sh.rmtree(PLAMYA_HOME)
    msg = "Ashes swept. The Forge is cold."
    console.print(f"  [dim]{msg}[/]\n") if HAS_RICH else print(f"  {msg}\n")


def cmd_rise():
    """Deploy."""
    if HAS_RICH:
        console.print()
        console.print("  [bold #f28c28]\u2592\u2592\u2592[/] [bold]Spreading...[/]")
        console.print()
        console.print("  [dim]Deploy is project-specific. See your agent docs.[/]")
        console.print()
    else:
        print("\n  >>> Spreading...\n  Deploy is project-specific.\n")


def cmd_version():
    if HAS_RICH:
        console.print(f"  [bold #f28c28]plamya[/] [dim]{VERSION}[/]")
    else:
        print(f"  plamya {VERSION}")


# ── Plain fallbacks (no rich) ───────────────────────────────────

def _cmd_status_plain():
    print("\n  The Forge  " + str(PLAMYA_HOME))
    print("  " + "-" * 50)
    checks = check_forge()
    for label, value, ok in checks:
        # Strip rich markup for plain mode
        import re
        clean = re.sub(r"\[.*?\]", "", value)
        icon = "*" if ok else "o"
        print(f"  {icon} {label}: {clean}")
    print()


def _cmd_help_plain():
    print("\n  Commands:\n")
    cmds = [
        ("ignite",  "Initialize The Forge"),
        ("status",  "Show system status"),
        ("spark",   "Create a new agent"),
        ("rise",    "Deploy"),
        ("ash",     "Cleanup"),
        ("version", "Show version"),
        ("help",    "Show this help"),
    ]
    for n, d in cmds:
        print(f"    {n.ljust(10)} {d}")
    print()


# ── Interactive REPL ─────────────────────────────────────────────

def interactive():
    """Interactive mode with banner + REPL."""
    print_banner()
    cmd_status()
    cmd_help()

    prompt = "  [bold #f28c28]plamya[/] [dim]>[/] " if HAS_RICH else "  plamya > "

    while True:
        try:
            if HAS_RICH:
                raw = console.input(prompt).strip()
            else:
                raw = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            msg = "The fire rests. Phoenix protocol: Ctrl+C to wake."
            if HAS_RICH:
                console.print(f"\n  [dim]{msg}[/]")
            else:
                print(f"\n  {msg}")
            break

        if not raw:
            continue

        command = raw.split()[0].lower()
        dispatch = {
            "status": cmd_status, "ignite": cmd_ignite,
            "spark": cmd_spark, "rise": cmd_rise,
            "ash": cmd_ash, "version": cmd_version, "help": cmd_help,
        }

        if command in ("exit", "quit", "q"):
            msg = "The fire rests."
            console.print(f"  [dim]{msg}[/]") if HAS_RICH else print(f"  {msg}")
            break
        elif command in dispatch:
            dispatch[command]()
        else:
            if HAS_RICH:
                console.print(f"  [red]?[/] Unknown: [bold]{command}[/]. Type [bold #f28c28]help[/]")
            else:
                print(f"  ? Unknown: {command}. Type help")


# ── Entry ────────────────────────────────────────────────────────

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = sys.argv[1:]
    if not args:
        interactive()
        return

    command = args[0].lower()
    dispatch = {
        "ignite": cmd_ignite, "status": cmd_status,
        "spark": cmd_spark, "rise": cmd_rise, "ash": cmd_ash,
        "version": cmd_version, "help": cmd_help,
        "--help": cmd_help, "-h": cmd_help,
        "--version": cmd_version, "-v": cmd_version,
    }
    fn = dispatch.get(command)
    if fn:
        if command not in ("version", "--version", "-v"):
            print_banner()
        fn()
    else:
        print_banner()
        if HAS_RICH:
            console.print(f"  [red]?[/] Unknown command: [bold]{command}[/]")
        else:
            print(f"  ? Unknown command: {command}")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

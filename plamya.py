#!/usr/bin/env python3
"""PLAMYA CLI - From ashes, autonomy."""

import os
import sys
import time
import json
import shutil
import random
from pathlib import Path

VERSION = "0.1.0"
PLAMYA_HOME = Path.home() / ".plamya"

# ── Rich imports (graceful fallback) ─────────────────────────────

def _enable_windows_ansi():
    """Enable ANSI escape codes in Windows terminal (PowerShell/cmd).
    Must be called BEFORE creating Rich Console."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 0x0004 | 0x0001)
    except Exception:
        pass

# Enable ANSI BEFORE importing Rich so it detects truecolor support
_enable_windows_ansi()

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console(color_system="truecolor") if HAS_RICH else None

# ── Flame Palette (3 shades like OpenClaw's lobster palette) ─────

FLAME_BRIGHT = "#FF7A3D"    # bright flame (solid blocks █)
FLAME_BASE   = "#FF5A2D"    # base flame (half blocks ▀▄)
FLAME_DIM    = "#D14A22"    # dim ember (shade blocks ░)
MUTED        = "#8B7F77"    # structure / borders
EMBER        = "#FF8A5B"    # warm info accent

# ── Block Art Banner ─────────────────────────────────────────────

# "PLAMYA" spelled in 3-row block characters.
# Each letter is 5 chars wide, separated by 2 spaces.
# Characters: █ (solid/bright), ▀▄ (half/base), ░ (shade/dim)
BLOCK_ART = [
    "█▀▀▀▄  █      ▄▀▀▄   █▄░▄█  █▄ ▄█  ▄▀▀▄",
    "█▄▄▄▀  █      █▀▀█   █░▀░█   ░█░   █▀▀█",
    "█      ▀▀▀▀▀  █  █   █   █   ░█░   █  █",
]

TAGLINES = [
    "From ashes, autonomy.",
    "Your agents just caught fire.",
    "Secure. Autonomous. Relentless.",
    "The phoenix protocol is active.",
    "Four guards. Zero trust. Full autonomy.",
    "Where prompt injection comes to die.",
    "Born in fire, forged in code.",
    "Ashes to agents.",
    "The ember glows. The forge awaits.",
    "AI agents with a survival instinct.",
]

def _get_tagline():
    """Pick a tagline — holiday-aware + random rotation."""
    now = time.localtime()
    m, d = now.tm_mon, now.tm_mday
    if m == 1 and d == 1:
        return "New year, new embers."
    if m == 12 and 24 <= d <= 26:
        return "Even phoenixes take holidays. Almost."
    return random.choice(TAGLINES)


def _colorize_block_char(ch):
    """Color each character by type — creates depth effect."""
    if ch == "█":
        return FLAME_BRIGHT
    if ch in ("▀", "▄"):
        return FLAME_BASE
    if ch == "░":
        return FLAME_DIM
    if ch == " ":
        return None
    return FLAME_BASE  # letters, other chars


def get_banner_art():
    """Build PLAMYA block art as Rich Text with per-character coloring."""
    if not HAS_RICH:
        lines = BLOCK_ART[:]
        lines.append("")
        lines.append(f"  PLAMYA v{VERSION}")
        lines.append(f'  "{_get_tagline()}"')
        return "\n".join("    " + l for l in lines) + "\n"

    t = Text()
    for line in BLOCK_ART:
        for ch in line:
            color = _colorize_block_char(ch)
            if color:
                t.append(ch, style=f"bold {color}")
            else:
                t.append(ch)
        t.append("\n")
    return t


# ── Fire ignition animation ─────────────────────────────────────

EMBER_COLORS = ["#3D0C02", "#6B1A0A", "#A03012", "#D14A22", "#FF5A2D", "#FF7A3D", "#FF9955", "#FFBB77"]


def _build_fire_frame(width, height, density, char_pool, color_idx):
    """Build one frame of random fire noise."""
    t = Text(justify="center")
    ci = min(color_idx, len(EMBER_COLORS) - 1)
    for row in range(height):
        for col in range(width):
            if random.random() < density:
                ch = random.choice(char_pool)
                t.append(ch, style=f"bold {EMBER_COLORS[ci]}")
            else:
                t.append(" ")
        if row < height - 1:
            t.append("\n")
    return t


def _build_reveal_frame(width, height, progress):
    """Build a frame where logo chars are revealed from center outward.
    progress: 0.0 (all fire) → 1.0 (all logo)."""
    t = Text(justify="center")
    center = width / 2
    max_dist = width / 2
    reveal_radius = progress * max_dist * 1.3  # overshoot slightly

    for row in range(height):
        line = BLOCK_ART[row] if row < len(BLOCK_ART) else ""
        for col in range(width):
            ch = line[col] if col < len(line) else " "
            dist = abs(col - center)

            if dist < reveal_radius and ch != " ":
                # Logo char revealed
                color = _colorize_block_char(ch)
                t.append(ch, style=f"bold {color}" if color else "")
            elif dist < reveal_radius:
                # Space in logo area — keep clean
                t.append(" ")
            elif random.random() < 0.35 * (1.0 - progress):
                # Fire noise fading out
                fch = random.choice("░▒▓")
                ci = min(int(4 + progress * 3), len(EMBER_COLORS) - 1)
                t.append(fch, style=f"bold {EMBER_COLORS[ci]}")
            else:
                t.append(" ")
        if row < height - 1:
            t.append("\n")
    return t


def _animate_ignition():
    """Animate fire ignition — embers crackle, logo reveals from center."""
    if not HAS_RICH:
        return

    try:
        from rich.live import Live
    except ImportError:
        return

    width = max(len(line) for line in BLOCK_ART)
    height = len(BLOCK_ART)

    with Live(Text(" "), console=console, refresh_per_second=20, transient=True) as live:
        # Phase 1 — dark embers spark up (4 frames, ~0.28s)
        for i in range(4):
            density = 0.05 + i * 0.08
            frame = _build_fire_frame(width, height, density, "░▒", i)
            live.update(frame)
            time.sleep(0.07)

        # Phase 2 — fire roars (4 frames, ~0.28s)
        for i in range(4):
            density = 0.3 + i * 0.1
            pool = "░▒▓█"[:2 + i]
            frame = _build_fire_frame(width, height, density, pool, 2 + i)
            live.update(frame)
            time.sleep(0.07)

        # Phase 3 — logo reveals from center outward (6 frames, ~0.42s)
        for i in range(6):
            progress = (i + 1) / 6
            frame = _build_reveal_frame(width, height, progress)
            live.update(frame)
            time.sleep(0.07)


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

def print_banner(animate=True):
    """Print the PLAMYA banner — block art + tagline."""
    if not HAS_RICH:
        print(get_banner_art())
        return

    console.print()

    # Fire ignition animation (only on interactive start)
    if animate:
        _animate_ignition()

    # Final logo
    art = get_banner_art()
    console.print(art, justify="center")

    # Title + version line
    title = Text()
    title.append("\U0001f525 ", style="bold")
    title.append("PLAMYA", style=f"bold {FLAME_BRIGHT}")
    title.append(f" v{VERSION}", style=f"{MUTED}")
    console.print(title, justify="center")

    # Tagline
    tagline = Text(_get_tagline(), style=f"italic {FLAME_DIM}")
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
        border_style="#FF5A2D",
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
    table.add_column("cmd", style="bold #FF5A2D", width=12)
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
        console.print("  [bold #FF5A2D]\u2592\u2592\u2592[/] [bold]Igniting The Forge...[/]")
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
        name = console.input("  [bold #FF5A2D]?[/] Agent name: ").strip().lower()
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
        console.print("  [bold #FF5A2D]\u2592\u2592\u2592[/] [bold]Spreading...[/]")
        console.print()
        console.print("  [dim]Deploy is project-specific. See your agent docs.[/]")
        console.print()
    else:
        print("\n  >>> Spreading...\n  Deploy is project-specific.\n")


def cmd_version():
    if HAS_RICH:
        console.print(f"  [bold #FF5A2D]plamya[/] [dim]{VERSION}[/]")
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

    prompt = "  [bold #FF5A2D]plamya[/] [dim]>[/] " if HAS_RICH else "  plamya > "

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
                console.print(f"  [red]?[/] Unknown: [bold]{command}[/]. Type [bold #FF5A2D]help[/]")
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
            print_banner(animate=False)
        fn()
    else:
        print_banner(animate=False)
        if HAS_RICH:
            console.print(f"  [red]?[/] Unknown command: [bold]{command}[/]")
        else:
            print(f"  ? Unknown command: {command}")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

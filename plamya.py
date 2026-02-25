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


def supports_color():
    if os.getenv("NO_COLOR"):
        return False
    if sys.platform == "win32":
        return (os.getenv("WT_SESSION") or os.getenv("TERM_PROGRAM")
                or "256color" in os.getenv("TERM", ""))
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = supports_color()


def _c(code, text):
    if not USE_COLOR:
        return text
    return "\033[" + code + "m" + text + "\033[0m"


def orange(t): return _c("38;5;208", t)
def red(t):    return _c("38;5;196", t)
def yellow(t): return _c("38;5;220", t)
def dim(t):    return _c("38;5;240", t)
def green(t):  return _c("38;5;82", t)
def cyan(t):   return _c("38;5;39", t)
def bold(t):   return _c("1", t)


def get_phoenix():
    r, o, y, d = red, orange, yellow, dim
    lines = [
        r("            ,  ,"),
        r("          ,  ,:"),
        o("         , ,::") + r("'"),
        o("        ,',:::"),
        y("    _") + o(",',::::") + y("_"),
        y("   (") + o("\\\\") + y(":::::") + o("//") + y(")"),
        y("    \\ ") + o("':::'") + y(" /"),
        y("     \\ ") + r("'v'") + y(" /"),
        y("      )   ("),
        y("     / ") + d("_") + y("   \\   ") + d("_"),
        y("    /") + d("| |") + y(" | ") + d("| |") + y("\\"),
        d("   /_|_|") + y("_|") + d("_|_|\\_"),
    ]
    return "\n".join(lines)


def print_banner():
    print()
    print(get_phoenix())
    print()
    print("  " + bold(orange("P L A M Y A")) + "   " + dim("v" + VERSION))
    q = chr(34)
    print("  " + dim(q + "From ashes, autonomy." + q))
    print()


def print_divider():
    w = min(shutil.get_terminal_size((80, 24)).columns, 60)
    print(dim("-" * w))


def sline(label, value, ok=True):
    icon = green("*") if ok else red("o")
    print("  " + icon + " " + dim(label + ":") + "  " + value)


# ---- Commands ----

def cmd_status():
    print()
    print("  " + bold("The Forge") + "  " + dim(str(PLAMYA_HOME)))
    print_divider()

    if not PLAMYA_HOME.exists():
        sline("State", red("not initialized") + "  " + dim("(run: plamya ignite)"), ok=False)
    else:
        sline("State", str(PLAMYA_HOME))

    embers_dir = PLAMYA_HOME / "embers"
    if embers_dir.exists():
        agents = list(embers_dir.glob("*.json"))
        if agents:
            names = ", ".join(a.stem for a in agents)
            sline("Agents", str(len(agents)) + " ember(s): " + cyan(names))
        else:
            sline("Agents", dim("no embers found"), ok=False)
    else:
        sline("Agents", dim("no embers directory"), ok=False)

    status_file = PLAMYA_HOME / "shared" / "STATUS.md"
    if status_file.exists():
        ago = int(time.time() - status_file.stat().st_mtime)
        if ago < 60:
            age = str(ago) + "s ago"
        elif ago < 3600:
            age = str(ago // 60) + "m ago"
        else:
            age = str(ago // 3600) + "h ago"
        sline("Heartbeat", "last pulse " + green(age))
    else:
        sline("Heartbeat", dim("no pulse"), ok=False)

    secrets_dir = PLAMYA_HOME / "secrets"
    if secrets_dir.exists():
        sline("Secrets", green("encrypted"))
    else:
        sline("Secrets", dim("not configured"), ok=False)

    claude_path = shutil.which("claude") or shutil.which("claude.cmd")
    if claude_path:
        sline("AI Engine", "Claude CLI  " + dim(claude_path))
    else:
        sline("AI Engine", orange("Claude CLI not found") + dim("  (fallback: API keys)"), ok=False)

    guards = ["input_guard", "output_guard", "action_guard", "canary"]
    shared_dir = Path(__file__).parent / "shared"
    found = [g for g in guards if (shared_dir / (g + ".py")).exists()]
    if len(found) == 4:
        sline("Security", green("4-layer defense active"))
    else:
        sline("Security", str(len(found)) + "/4 guards", ok=len(found) == 4)
    print()


def cmd_ignite():
    print()
    print("  " + orange(">>>") + " " + bold("Igniting The Forge..."))
    print()
    dirs = [
        PLAMYA_HOME,
        PLAMYA_HOME / "embers",
        PLAMYA_HOME / "shared",
        PLAMYA_HOME / "secrets",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print("  " + green("+") + " " + str(d))

    if sys.platform != "win32":
        os.chmod(PLAMYA_HOME / "secrets", 0o700)

    sf = PLAMYA_HOME / "shared" / "STATUS.md"
    if not sf.exists():
        sf.write_text("# PLAMYA Agent Status\n\nNo agents running yet.\n", encoding="utf-8")
        print("  " + green("+") + " " + str(sf))

    ib = PLAMYA_HOME / "shared" / "INBOX.md"
    if not ib.exists():
        ib.write_text("# PLAMYA Inbox\n\nNo messages.\n", encoding="utf-8")
        print("  " + green("+") + " " + str(ib))

    print()
    print("  " + green("The Forge is lit.") + " " + dim("Add agent configs to embers/"))
    print("  " + dim("See: examples/chappie/ for how to create an agent"))
    print()


def cmd_spark():
    print()
    try:
        name = input("  " + orange("?") + " Agent name: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return
    if not name:
        print("  " + red("!") + " Name required")
        return
    if not name.isidentifier():
        print("  " + red("!") + " Name must be a valid Python identifier")
        return

    embers_dir = PLAMYA_HOME / "embers"
    embers_dir.mkdir(parents=True, exist_ok=True)
    cf = embers_dir / (name + ".json")
    if cf.exists():
        print("  " + orange("!") + " Ember already exists: " + str(cf))
        return

    config = {
        "name": name,
        "description": name + " agent",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "allowed_actions": ["get_status"],
    }
    cf.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print("  " + green("+") + " Ember: " + str(cf))

    ad = PLAMYA_HOME / name
    ad.mkdir(parents=True, exist_ok=True)
    print("  " + green("+") + " State: " + str(ad))
    print()
    print("  " + green("Spark created.") + " " + dim("The ember glows, waiting to be fanned."))
    print()


def cmd_ash():
    print()
    if not PLAMYA_HOME.exists():
        print("  " + dim("Nothing to clean. The Forge is cold."))
        return
    try:
        ans = input("  " + red("?") + " Sweep the ashes from " + str(PLAMYA_HOME) + "? [y/N] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return
    if ans != "y":
        print("  " + dim("Cancelled."))
        return
    import shutil as sh
    sh.rmtree(PLAMYA_HOME)
    print("  " + dim("Ashes swept. The Forge is cold."))
    print()


def cmd_rise():
    print()
    print("  " + orange(">>>") + " " + bold("Spreading..."))
    print()
    print("  " + dim("Deploy is project-specific. See your agent docs."))
    print()


def cmd_version():
    print("  plamya " + VERSION)


def cmd_help():
    print()
    print("  " + bold("Commands:"))
    print()
    cmds = [
        ("ignite",  "Initialize The Forge, create ~/.plamya/"),
        ("status",  "Show agent status and system health"),
        ("spark",   "Create a new agent (ember + state dir)"),
        ("rise",    "Deploy (project-specific)"),
        ("ash",     "Cleanup - sweep the ashes"),
        ("version", "Show version"),
        ("help",    "Show this help"),
    ]
    for n, d in cmds:
        print("    " + cyan(n.ljust(10)) + " " + d)
    print()


# ---- Interactive ----

def interactive():
    print_banner()
    print_divider()
    cmd_status()
    print_divider()
    cmd_help()
    while True:
        try:
            raw = input("  " + orange("plamya") + " " + dim(">") + " ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  " + dim("The fire rests. Phoenix protocol: Ctrl+C to wake."))
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
            print("  " + dim("The fire rests."))
            break
        elif command in dispatch:
            dispatch[command]()
        else:
            print("  " + red("?") + " Unknown: " + command + ". Type " + cyan("help"))


# ---- Entry ----

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
        print("  " + red("?") + " Unknown command: " + command)
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

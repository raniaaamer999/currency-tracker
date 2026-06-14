"""
display.py
----------
Terminal output helpers.

Keeps all formatting logic in one place so the main CLI stays readable.
Uses ANSI colour codes for a polished terminal experience — standard on
macOS, Linux, and Windows Terminal.
"""

from typing import Optional


# ─── ANSI colour helpers ──────────────────────────────────────────────────────

class Colour:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"
    MAGENTA = "\033[95m"

def bold(text: str) -> str:
    return f"{Colour.BOLD}{text}{Colour.RESET}"

def green(text: str) -> str:
    return f"{Colour.GREEN}{text}{Colour.RESET}"

def red(text: str) -> str:
    return f"{Colour.RED}{text}{Colour.RESET}"

def cyan(text: str) -> str:
    return f"{Colour.CYAN}{text}{Colour.RESET}"

def yellow(text: str) -> str:
    return f"{Colour.YELLOW}{text}{Colour.RESET}"

def dim(text: str) -> str:
    return f"{Colour.DIM}{text}{Colour.RESET}"


# ─── Reusable layout pieces ───────────────────────────────────────────────────

def header(title: str, width: int = 60):
    """Print a styled section header."""
    line = "─" * width
    print(f"\n{cyan(line)}")
    print(f"  {bold(title)}")
    print(f"{cyan(line)}")


def divider(width: int = 60):
    print(dim("─" * width))


def print_rates_table(base: str, rates: dict[str, float], currency_names: dict[str, str]):
    """
    Pretty-print a table of exchange rates.

    Args:
        base: Base currency code
        rates: Dict of {target_code: rate}
        currency_names: Dict of {code: full_name}
    """
    header(f"Exchange Rates  ·  Base: {base}")
    print(f"  {'CODE':<6}  {'CURRENCY':<22}  {'RATE':>12}")
    divider()
    for code, rate in sorted(rates.items()):
        name = currency_names.get(code, code)
        # Format rates sensibly: JPY-style integers vs decimal currencies
        rate_str = f"{rate:>12.2f}" if rate >= 100 else f"{rate:>12.4f}"
        print(f"  {cyan(code):<15}  {dim(name):<22}  {bold(rate_str)}")
    divider()


def print_history_chart(history: list[dict], base: str, target: str, width: int = 40):
    """
    Print a simple ASCII sparkline chart of rate history.

    Args:
        history: List of dicts with 'rate_date' and 'rate' keys (newest first)
        base: Base currency
        target: Target currency
        width: Width of the chart in characters
    """
    if not history:
        print(yellow("  No history stored yet. Fetch rates a few times to build history."))
        return

    # Reverse to chronological order for display
    history = list(reversed(history))
    rates = [h["rate"] for h in history]
    lo, hi = min(rates), max(rates)
    spread = hi - lo or 1  # Avoid division by zero if all rates are equal

    header(f"Rate History  ·  {base}/{target}  ({len(history)} data points)")

    # Sparkline using block characters
    BLOCKS = " ▁▂▃▄▅▆▇█"
    spark = ""
    for r in rates:
        idx = int((r - lo) / spread * (len(BLOCKS) - 1))
        spark += BLOCKS[idx]

    print(f"\n  {cyan(spark)}\n")
    print(f"  {dim('Low:')}  {lo:.4f}    {dim('High:')}  {hi:.4f}    {dim('Latest:')}  {rates[-1]:.4f}")

    # Print last 7 date/rate pairs in a mini-table
    print()
    print(f"  {dim('Recent readings:')}")
    for entry in history[-7:]:
        print(f"    {dim(entry['rate_date'])}   {entry['rate']:.4f}")
    divider()


def print_alerts_table(alerts: list[dict]):
    """Print a table of all user alerts."""
    if not alerts:
        print(yellow("  No alerts set."))
        return

    header("Active Alerts")
    print(f"  {'ID':<4}  {'PAIR':<10}  {'DIR':<6}  {'TARGET':>10}  {'STATUS'}")
    divider()
    for a in alerts:
        pair = f"{a['base']}/{a['target']}"
        status = green("✓ triggered") if a["triggered"] else yellow("⏳ pending")
        triggered_rate = f"(hit {a['triggered_rate']:.4f})" if a["triggered"] else ""
        print(
            f"  {a['id']:<4}  {pair:<10}  {a['direction']:<6}  "
            f"{a['target_rate']:>10.4f}  {status} {dim(triggered_rate)}"
        )
    divider()


def error(msg: str):
    print(f"\n{red('✗')} {msg}")


def success(msg: str):
    print(f"\n{green('✓')} {msg}")


def info(msg: str):
    print(f"\n{cyan('ℹ')} {msg}")

"""Read-only macOS system telemetry via built-in tools. Nothing here is a temperature reading:
this Mac exposes no GPU temperature/clock without sudo (powermetrics), and none is fabricated."""
from __future__ import annotations

import re
import subprocess

PRESSURE_LEVELS = {1: "normal", 2: "warn", 4: "critical"}


def _run(cmd: list[str], timeout: float = 5.0) -> str | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def memory_telemetry() -> dict:
    out: dict = {}
    lvl = _run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"])
    if lvl and lvl.strip().isdigit():
        out["pressure_level"] = PRESSURE_LEVELS.get(int(lvl), f"unknown({lvl.strip()})")
    swap = _run(["sysctl", "-n", "vm.swapusage"])
    if swap:
        m = re.search(r"used = ([\d.]+)M", swap)
        t = re.search(r"total = ([\d.]+)M", swap)
        if m:
            out["swap_used_gb"] = round(float(m.group(1)) / 1024, 2)
        if t:
            out["swap_total_gb"] = round(float(t.group(1)) / 1024, 2)
    mp = _run(["memory_pressure"])
    if mp:
        m = re.search(r"free percentage:\s*(\d+)%", mp)
        if m:
            out["free_percent"] = int(m.group(1))
    vs = _run(["vm_stat"])
    if vs:
        page = int((re.search(r"page size of (\d+)", vs) or [None, 16384])[1])
        for key, label in (("Pages occupied by compressor", "compressed_gb"), ("Pages wired down", "wired_gb")):
            m = re.search(rf"{key}:\s+(\d+)", vs)
            if m:
                out[label] = round(int(m.group(1)) * page / 1e9, 2)
    return out


def thermal_telemetry() -> dict:
    """pmset reports only whether the OS has recorded a thermal/performance warning level."""
    t = _run(["pmset", "-g", "therm"])
    if t is None:
        return {"available": False}
    return {
        "source": "pmset -g therm (warning levels only; not a temperature)",
        "thermal_warning_recorded": "No thermal warning level has been recorded" not in t,
        "performance_warning_recorded": "No performance warning level has been recorded" not in t,
    }


def power_source() -> str | None:
    b = _run(["pmset", "-g", "batt"])
    if not b:
        return None
    m = re.search(r"Now drawing from '([^']+)'", b)
    return m.group(1) if m else None

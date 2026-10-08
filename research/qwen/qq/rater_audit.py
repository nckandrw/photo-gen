"""Audit of the Q-Q rater subagent's tool calls (PROTOCOL.md §6): what it read, wrote and ran, and whether anything
touched a path outside the blind directory and its crop directory. Reads the session-local subagent transcript
(JSONL, not committed); writes a committed summary. Heredoc bodies (score rows) are excluded from the path scan.

Usage: python3 research/qwen/qq/rater_audit.py <subagent.jsonl> <blind_dir> <crops_dir> <out.json>"""
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path


def main(transcript: str, blind: str, crops: str, out: str) -> None:
    blind, crops = str(Path(blind).resolve()), str(Path(crops).resolve())
    allowed = (blind, crops, "/private" + crops if not crops.startswith("/private") else crops[len("/private"):])
    calls, reads, writes, programs, outside = Counter(), Counter(), [], Counter(), []
    sensitive = []
    for line in Path(transcript).read_text().splitlines():
        d = json.loads(line)
        m = d.get("message") or {}
        if not isinstance(m, dict) or not isinstance(m.get("content"), list):
            continue
        for c in m["content"]:
            if c.get("type") != "tool_use":
                continue
            name, inp = c["name"], c.get("input") or {}
            calls[name] += 1
            paths = []
            if name == "Read":
                p = inp.get("file_path", "")
                paths.append(p)
                reads[p.replace(blind + "/", "blind/").replace(crops + "/", "crops/")] += 1
            elif name in ("Write", "Edit"):
                p = inp.get("file_path", "")
                paths.append(p)
                writes.append(p)
            elif name == "Bash":
                cmd = re.sub(r"<<-?\s*'?(\w+)'?.*?\n\1\b", "<<HEREDOC", inp.get("command", ""), flags=re.S)
                for seg in re.split(r"[;&|\n]+", cmd):
                    w = seg.strip().split()
                    if w:
                        programs[w[0]] += 1
                paths += re.findall(r"(/(?:Users|private|tmp|var|etc|opt)[^\s'\"<>|;)]*)", cmd)
                for s in ("KEY-DO-NOT-OPEN", "key-unblinded", "research/qwen/runs", "MANIFEST.json", "qq-summary",
                          "git ", "PROTOCOL.md", "SCORES-FROZEN"):
                    if s in cmd:
                        sensitive.append([name, s])
            else:
                paths += [v for v in inp.values() if isinstance(v, str) and v.startswith("/")]
            for p in paths:
                rp = p.rstrip("/")
                if rp and not any(rp == a or rp.startswith(a + "/") for a in allowed):
                    outside.append([name, p])
            for p in paths:
                if any(s in p for s in ("KEY-DO-NOT-OPEN", "key-unblinded", "/runs/", "MANIFEST.json", "SCORES-FROZEN")):
                    sensitive.append([name, p])
    rec = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "method": "extracted from the rater subagent's tool-call transcript (session-local, not committed); heredoc "
                     "bodies excluded from the path scan",
           "allowed": {"blind": blind, "crops": crops}, "tool_calls": dict(calls), "reads": dict(reads),
           "writes": sorted(set(writes)), "bash_programs": dict(programs), "paths_outside_allowed": outside,
           "sensitive_access": sensitive}
    Path(out).write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("tool_calls", "writes", "paths_outside_allowed", "sensitive_access")}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])

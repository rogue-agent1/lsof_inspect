#!/usr/bin/env python3
"""lsof_inspect - Inspect open files, ports, and connections.

One file. Zero deps. See what's open.

Usage:
  lsof_inspect.py ports              → listening ports with PIDs
  lsof_inspect.py connections        → active network connections
  lsof_inspect.py pid 1234           → files open by PID
  lsof_inspect.py file /path/to/file → who has this file open
  lsof_inspect.py port 8080          → who's using port 8080
  lsof_inspect.py user root          → files open by user
  lsof_inspect.py summary            → open file stats
"""

import argparse
import os
import re
import subprocess
import sys


def run(cmd: str) -> str:
    try:
        env = os.environ.copy()
        env["PATH"] = "/usr/sbin:/usr/bin:/bin:/sbin:" + env.get("PATH", "")
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, env=env)
        return r.stdout.strip()
    except Exception:
        return ""


def cmd_ports(args):
    out = run("lsof -i -P -n 2>/dev/null | grep LISTEN")
    if not out:
        print("No listening ports found")
        return
    seen = set()
    print(f"  {'PROCESS':20s} {'PID':>7s}  {'PORT'}")
    for line in out.split("\n"):
        parts = line.split()
        if len(parts) < 9:
            continue
        proc, pid, addr = parts[0], parts[1], parts[8]
        key = f"{pid}:{addr}"
        if key in seen:
            continue
        seen.add(key)
        port = addr.rsplit(":", 1)[-1] if ":" in addr else addr
        print(f"  {proc:20s} {pid:>7s}  {port}")


def cmd_connections(args):
    out = run("lsof -i -P -n 2>/dev/null | grep ESTABLISHED")
    if not out:
        out = run("lsof -i -P -n 2>/dev/null | grep -E '->|UDP'")
    if not out:
        print("No active connections")
        return
    print(f"  {'PROCESS':15s} {'PID':>7s}  {'CONNECTION'}")
    for line in out.split("\n")[:30]:
        parts = line.split()
        if len(parts) < 9:
            continue
        print(f"  {parts[0]:15s} {parts[1]:>7s}  {parts[8]}")


def cmd_pid(args):
    out = run(f"lsof -p {args.pid} 2>/dev/null")
    if not out:
        print(f"No open files for PID {args.pid}")
        return
    lines = out.split("\n")
    types = {}
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 5:
            t = parts[4]
            types[t] = types.get(t, 0) + 1
    print(f"  PID {args.pid}: {len(lines)-1} open files")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"    {t:10s} {c}")


def cmd_file(args):
    out = run(f"lsof {args.path} 2>/dev/null")
    if not out:
        print(f"No processes have '{args.path}' open")
        return
    for line in out.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and parts[0] != "COMMAND":
            print(f"  {parts[0]:20s} PID {parts[1]}")


def cmd_port(args):
    out = run(f"lsof -i :{args.port} -P -n 2>/dev/null")
    if not out:
        print(f"Nothing using port {args.port}")
        return
    for line in out.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and parts[0] != "COMMAND":
            state = parts[-1] if "(" in parts[-1] else ""
            print(f"  {parts[0]:20s} PID {parts[1]:>7s}  {state}")


def cmd_user(args):
    out = run(f"lsof -u {args.user} 2>/dev/null | head -50")
    if not out:
        print(f"No files open by user '{args.user}'")
        return
    total = run(f"lsof -u {args.user} 2>/dev/null | wc -l").strip()
    print(f"  User '{args.user}': ~{total} open files")
    procs = {}
    for line in out.split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 2:
            procs[parts[0]] = procs.get(parts[0], 0) + 1
    for proc, count in sorted(procs.items(), key=lambda x: -x[1])[:15]:
        print(f"    {proc:20s} {count} files")


def cmd_summary(args):
    total = run("lsof 2>/dev/null | wc -l").strip()
    print(f"  Total open files: ~{total}")
    out = run("lsof 2>/dev/null | awk '{print $1}' | sort | uniq -c | sort -rn | head -10")
    if out:
        print(f"  Top processes:")
        for line in out.split("\n"):
            parts = line.strip().split()
            if len(parts) == 2:
                print(f"    {parts[1]:20s} {parts[0]} files")


def main():
    p = argparse.ArgumentParser(description="Inspect open files and connections")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("ports").set_defaults(func=cmd_ports)
    sub.add_parser("connections").set_defaults(func=cmd_connections)
    sub.add_parser("summary").set_defaults(func=cmd_summary)

    s = sub.add_parser("pid")
    s.add_argument("pid", type=int)
    s.set_defaults(func=cmd_pid)

    s = sub.add_parser("file")
    s.add_argument("path")
    s.set_defaults(func=cmd_file)

    s = sub.add_parser("port")
    s.add_argument("port", type=int)
    s.set_defaults(func=cmd_port)

    s = sub.add_parser("user")
    s.add_argument("user")
    s.set_defaults(func=cmd_user)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())

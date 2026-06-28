#!/usr/bin/env python3
"""Count the total number of IP addresses covered by CIDR networks read on stdin.

Reads CIDR networks (one per line, or whitespace/comma separated) from stdin and
prints how many addresses they cover in total. IPv4 and IPv6 are counted
separately because their address spaces are not comparable.

By default overlapping/duplicate networks are counted as many times as they
appear. Use --unique to collapse overlaps first so every address is counted once.

Examples:
    cat nets.txt | ./count_ips.py
    ./count_ips.py --unique < nets.txt
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
from typing import Iterable, List

IPNetwork = ipaddress._BaseNetwork  # IPv4Network | IPv6Network


def parse_input(stream: Iterable[str]) -> List[IPNetwork]:
    nets: List[IPNetwork] = []
    for lineno, raw in enumerate(stream, 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        for token in line.replace(",", " ").split():
            try:
                nets.append(ipaddress.ip_network(token, strict=False))
            except ValueError as exc:
                print(f"count_ips: line {lineno}: skipping {token!r}: {exc}",
                      file=sys.stderr)
    return nets


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Count IP addresses covered by CIDR networks read from stdin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--unique", action="store_true",
                   help="collapse overlapping networks so each address counts once")
    return p


def main(argv: List[str]) -> int:
    args = build_parser().parse_args(argv)

    networks = parse_input(sys.stdin)
    v4 = [n for n in networks if n.version == 4]
    v6 = [n for n in networks if n.version == 6]

    if args.unique:
        v4 = list(ipaddress.collapse_addresses(v4))
        v6 = list(ipaddress.collapse_addresses(v6))

    count4 = sum(n.num_addresses for n in v4)
    count6 = sum(n.num_addresses for n in v6)

    if v4:
        print(f"IPv4: {count4}")
    if v6:
        print(f"IPv6: {count6}")
    if not v4 and not v6:
        print("IPv4: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

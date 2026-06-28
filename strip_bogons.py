#!/usr/bin/env python3
"""Filter out reserved/bogon CIDR networks from a list read on stdin.

Reads CIDR networks (one per line, or whitespace/comma separated) from stdin and
writes back only the parts that are NOT inside reserved address space defined by
various RFCs. Reserved ranges that are a subnet of an input network are excised,
splitting the input into the surrounding CIDR blocks; networks fully contained in
a reserved range are dropped entirely.

By default every known reserved group is removed. Use --rfc to restrict removal
to specific groups, or --keep to remove everything except the listed groups.

Examples:
    cat nets.txt | ./strip_bogons.py
    ./strip_bogons.py --rfc rfc1918,rfc6598 < nets.txt
    ./strip_bogons.py --keep rfc5737 --collapse < nets.txt
    ./strip_bogons.py --list
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
from typing import Dict, Iterable, List, Tuple

IPNetwork = ipaddress._BaseNetwork  # IPv4Network | IPv6Network

# Reserved address space grouped by the RFC (or role) that defines it.
# Keys are the selectable group names; values are (description, [cidrs]).
RESERVED: Dict[str, Tuple[str, List[str]]] = {
    # ---- IPv4 ----
    "rfc1918": ("Private-use networks", ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]),
    "rfc6598": ("Carrier-grade NAT shared space", ["100.64.0.0/10"]),
    "rfc1122": ("\"This host on this network\" + loopback", ["0.0.0.0/8", "127.0.0.0/8"]),
    "rfc3927": ("Link-local (APIPA)", ["169.254.0.0/16"]),
    "rfc5737": ("Documentation (TEST-NET)", ["192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"]),
    "rfc2544": ("Benchmarking", ["198.18.0.0/15"]),
    "rfc3068": ("6to4 relay anycast", ["192.88.99.0/24"]),
    "rfc1112": ("Reserved for future use (former class E)", ["240.0.0.0/4"]),
    "rfc5771": ("Multicast", ["224.0.0.0/4"]),
    "rfc919": ("Limited broadcast", ["255.255.255.255/32"]),
    # ---- IPv6 ----
    "rfc4291": ("Unspecified, loopback, link-local (IPv6)", ["::/128", "::1/128", "fe80::/10"]),
    "rfc4193": ("Unique local addresses (IPv6 ULA)", ["fc00::/7"]),
    "rfc3849": ("Documentation (IPv6)", ["2001:db8::/32"]),
    "rfc6666": ("Discard-only prefix (IPv6)", ["100::/64"]),
    "rfc4291mc": ("Multicast (IPv6)", ["ff00::/8"]),
}


def reserved_networks(groups: Iterable[str]) -> List[IPNetwork]:
    nets: List[IPNetwork] = []
    for g in groups:
        for cidr in RESERVED[g][1]:
            nets.append(ipaddress.ip_network(cidr))
    return nets


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
                print(f"strip_bogons: line {lineno}: skipping {token!r}: {exc}",
                      file=sys.stderr)
    return nets


def exclude_reserved(networks: List[IPNetwork],
                     reserved: List[IPNetwork]) -> List[IPNetwork]:
    """Return networks with all reserved space removed.

    Relies on the CIDR property that any two overlapping networks are nested:
    one is always a subnet of the other.
    """
    result = list(networks)
    for r in reserved:
        carried: List[IPNetwork] = []
        for n in result:
            if n.version != r.version or not n.overlaps(r):
                carried.append(n)
                continue
            if r.prefixlen <= n.prefixlen:
                # r equals or contains n -> n is fully reserved, drop it.
                continue
            # r is strictly inside n -> split n around r.
            carried.extend(n.address_exclude(r))
        result = carried
    return result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Remove reserved/bogon CIDR networks read from stdin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--rfc", metavar="GROUPS",
                   help="comma-separated groups to remove (default: all)")
    p.add_argument("--keep", metavar="GROUPS",
                   help="comma-separated groups to NOT remove (remove all others)")
    p.add_argument("--collapse", action="store_true",
                   help="collapse the output into the minimal set of CIDRs")
    p.add_argument("--list", action="store_true",
                   help="list available groups and exit")
    return p


def split_groups(value: str) -> List[str]:
    groups = [g.strip().lower() for g in value.replace(",", " ").split() if g.strip()]
    unknown = [g for g in groups if g not in RESERVED]
    if unknown:
        raise SystemExit(f"strip_bogons: unknown group(s): {', '.join(unknown)}\n"
                         f"available: {', '.join(RESERVED)}")
    return groups


def main(argv: List[str]) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        width = max(len(k) for k in RESERVED)
        for name, (desc, cidrs) in RESERVED.items():
            print(f"{name:<{width}}  {desc}")
            print(f"{'':<{width}}    {', '.join(cidrs)}")
        return 0

    if args.rfc and args.keep:
        raise SystemExit("strip_bogons: --rfc and --keep are mutually exclusive")

    if args.rfc:
        selected = split_groups(args.rfc)
    elif args.keep:
        kept = set(split_groups(args.keep))
        selected = [g for g in RESERVED if g not in kept]
    else:
        selected = list(RESERVED)

    networks = parse_input(sys.stdin)
    cleaned = exclude_reserved(networks, reserved_networks(selected))

    if args.collapse:
        v4 = [n for n in cleaned if n.version == 4]
        v6 = [n for n in cleaned if n.version == 6]
        cleaned = list(ipaddress.collapse_addresses(v4)) + \
            list(ipaddress.collapse_addresses(v6))

    for net in cleaned:
        print(net.with_prefixlen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

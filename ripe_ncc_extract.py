#!/usr/bin/env python3
import sys
import argparse
import ipaddress
import gzip

def open_input(path):
    if not path or path == "-":
        return sys.stdin
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")

def parse_args():
    p = argparse.ArgumentParser(
        description="Extract IPv4/IPv6 networks in CIDR from a delegated RIR stats file filtered by country."
    )
    p.add_argument("file", nargs="?", help="Path to delegated-<registry>-latest (or .gz). Reads stdin if omitted or '-'.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--ipv4", action="store_true", help="Output only IPv4 networks")
    g.add_argument("--ipv6", action="store_true", help="Output only IPv6 networks")
    g.add_argument("--all", action="store_true", help="Output both IPv4 and IPv6 (default)")
    p.add_argument(
        "--countries", "-c",
        help="Comma-separated list of ISO country codes to include (e.g., US,DE). If omitted, all countries are included."
    )
    return p.parse_args()

def should_include_status(status):
    # Include typical allocation statuses; exclude available/reserved/etc.
    s = status.lower()
    return ("allocated" in s) or ("assigned" in s)

def main():
    args = parse_args()
    want_types = {"ipv4", "ipv6"}
    if args.ipv4:
        want_types = {"ipv4"}
    elif args.ipv6:
        want_types = {"ipv6"}
    # args.all or default => both

    countries = None
    if args.countries:
        countries = {c.strip().upper() for c in args.countries.split(",") if c.strip()}

    try:
        f = open_input(args.file)
    except Exception as e:
        print(f"Error opening input: {e}", file=sys.stderr)
        return 2

    out = sys.stdout
    with f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 7:
                continue
            registry, cc, rtype, start, value, date, status = parts[:7]

            rtype_lc = rtype.lower()
            if rtype_lc not in want_types:
                continue
            if countries is not None and cc.upper() not in countries:
                continue
            if not should_include_status(status):
                continue

            try:
                if rtype_lc == "ipv4":
                    count = int(value)
                    start_ip = ipaddress.IPv4Address(start)
                    end_ip = ipaddress.IPv4Address(int(start_ip) + count - 1)
                    for net in ipaddress.summarize_address_range(start_ip, end_ip):
                        print(str(net), file=out)
                elif rtype_lc == "ipv6":
                    prefix_len = int(value)  # per delegated stats, value is prefix length for IPv6
                    net = ipaddress.IPv6Network(f"{start}/{prefix_len}", strict=False)
                    print(str(net), file=out)
            except Exception:
                # Skip malformed entries gracefully
                continue

    return 0

if __name__ == "__main__":
    raise SystemExit(main())


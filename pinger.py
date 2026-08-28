#!/usr/bin/env python3
"""
Warm the ARP cache ahead of a port-map run by pinging every host in a set
of subnets.

port-map.py builds its switch-port-to-endpoint map from the ARP tables
collected by config-pull.py, so those tables have to be populated first.
Running this against the customer's user subnets a few minutes before the
discovery pass gives every reachable host an ARP entry on its gateway.

Being gentle on EDR / NDR
-------------------------
Customers increasingly run CrowdStrike, SentinelOne, Darktrace, etc. A
host that fires ICMP at every address in a subnet all at once looks exactly
like a horizontal scan and can get the source machine alerted on or
quarantined. This script defaults to a *paced* sweep:

  * --rate limits how many pings are started per second (default 20).
  * host order within each subnet is shuffled unless --in-order is given.
  * --count controls echoes per host (default 1, which is enough to
    populate an ARP entry).

--rate 0 restores the old "start everything at once" behaviour.

Input
-----
A text file (default: vlans.txt) with one subnet per line. Two formats are
accepted and may be mixed in the same file:

  * Pasted straight from a switch:

        show run | i ^interface|^ ip address

    interface Vlan10
     ip address 10.20.10.1 255.255.255.0

  * One subnet per line, as "address mask" or CIDR:

        10.20.10.0 255.255.255.0
        10.20.20.0/24

Blank lines, lines containing "interface", and lines starting with "#" are
ignored, so you can comment a subnet out by prefixing it with "#".

Subnets larger than --max-hosts addresses (default 2100, i.e. bigger than a
/21) are skipped.

Usage
-----
    python3 pinger.py
    python3 pinger.py --file user-subnets.txt --rate 10 --count 1
    python3 pinger.py --rate 0 --in-order        # old fast/noisy behaviour
"""

import argparse
import ipaddress
import platform
import random
import subprocess
import sys
import time


def build_ping_command(ip: str, system: str, count: int) -> list[str]:
    """Return the platform-appropriate ``ping`` argv for a single host.

    `count` ICMP echoes, numeric output, with a short overall deadline so a
    dead host does not hold the batch open.
    """
    n = str(count)
    if system == "Windows":
        return ["ping", "-n", n, "-w", "1000", ip]
    if system == "Darwin":
        # macOS: -t is the total timeout in seconds
        return ["ping", "-n", "-c", n, "-t", "4", ip]
    # Linux and everything else: -w is the deadline in seconds
    return ["ping", "-n", "-c", n, "-w", "4", ip]


def host_answered(output: bytes) -> bool:
    """True only if ping received a real ICMP echo reply.

    The exit code alone is not reliable on Windows: when a host in a
    directly-connected subnet does not exist, the local IP stack replies
    "Destination host unreachable", which Windows ping counts as a reply and
    exits 0. A genuine echo reply always carries "TTL=" (Windows) / "ttl="
    (Linux, macOS); the unreachable and timeout messages never do.
    """
    return b"ttl=" in output.lower()


def parse_subnet_line(line: str) -> str | None:
    """Turn one input line into an ``address/mask`` string, or None to skip it.

    Handles both the switch ``ip address <addr> <mask>`` form and a bare
    ``<addr> <mask>`` / ``<addr>/<prefix>`` line.
    """
    line = line.strip()
    if not line or line.startswith("#") or "interface" in line.lower():
        return None

    tokens = line.split()
    if len(tokens) >= 2 and tokens[0] == "ip" and tokens[1] == "address":
        tokens = tokens[2:]

    if len(tokens) == 1:
        return tokens[0]  # already CIDR, e.g. 10.20.10.0/24
    if len(tokens) == 2:
        return f"{tokens[0]}/{tokens[1]}"  # address + mask
    return None


def read_subnets(path: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Read the subnet file and return a list of validated networks."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except FileNotFoundError:
        print(f"{path} does not exist")
        return []

    subnets = []
    for line in lines:
        candidate = parse_subnet_line(line)
        if candidate is None:
            continue
        try:
            subnets.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            print(f"Skipping unrecognized subnet line: {line.strip()!r}")
    return subnets


def ping_hosts(
    hosts: list[str], system: str, count: int, rate: int
) -> dict[str, bool]:
    """Ping each host, starting at most `rate` pings per second (0 = no cap).

    Finished pings are collected as we go so the number of open processes
    and pipe handles stays small even on a large subnet.
    """
    interval = 1.0 / rate if rate > 0 else 0.0
    in_flight: dict[str, subprocess.Popen] = {}
    results: dict[str, bool] = {}

    def collect(block: bool) -> None:
        for ip in list(in_flight):
            proc = in_flight[ip]
            if not block and proc.poll() is None:
                continue
            output, _ = proc.communicate()
            results[ip] = host_answered(output)
            del in_flight[ip]

    for ip in hosts:
        in_flight[ip] = subprocess.Popen(
            build_ping_command(ip, system, count),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if interval:
            time.sleep(interval)
        collect(block=False)

    collect(block=True)
    return results


def ping_subnet(
    subnet, system: str, max_hosts: int, count: int, rate: int, shuffle: bool
) -> None:
    """Ping every usable host in one subnet and print which ones answer."""
    if subnet.num_addresses > max_hosts:
        print(f"Skipped {subnet} ({subnet.num_addresses} addresses > {max_hosts})")
        return

    hosts = [str(host) for host in subnet.hosts()]
    if shuffle:
        random.shuffle(hosts)

    print()
    print(f"Pinging {len(hosts)} hosts in {subnet}")
    results = ping_hosts(hosts, system, count, rate)

    print()
    print("------ Results from the Pings ------")
    for ip in sorted(results, key=ipaddress.ip_address):
        print(f"{ip} {'active' if results[ip] else 'no response'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ping every host in the subnets listed in a file to warm the ARP cache."
    )
    parser.add_argument(
        "-f", "--file", default="vlans.txt", help="subnet list file (default: vlans.txt)"
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=1,
        help="ICMP echo requests per host (default: 1, which is enough for ARP)",
    )
    parser.add_argument(
        "-r",
        "--rate",
        type=int,
        default=20,
        help="max pings started per second, 0 = no limit (default: 20)",
    )
    parser.add_argument(
        "--in-order",
        action="store_true",
        help="ping hosts low-to-high instead of in random order",
    )
    parser.add_argument(
        "-m",
        "--max-hosts",
        type=int,
        default=2100,
        help="skip subnets with more addresses than this (default: 2100)",
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.rate < 0:
        parser.error("--rate must be 0 (no limit) or a positive number")

    system = platform.system()
    echoes = "1 echo request" if args.count == 1 else f"{args.count} echo requests"
    print()
    print(f"OS is {system}, sending {echoes} per host")
    if args.in_order:
        print("IP addresses pinged in low-to-high order (--in-order)")
    else:
        print("IP addresses have been randomized")

    subnets = read_subnets(args.file)
    if not subnets:
        print("No subnets to ping.")
        sys.exit(1)

    to_ping = [s for s in subnets if s.num_addresses <= args.max_hosts]
    total_hosts = sum(sum(1 for _ in s.hosts()) for s in to_ping)
    print(f"Number of Subnets: {len(subnets)}")
    if args.rate > 0 and total_hosts:
        print(
            f"{total_hosts} hosts to ping at {args.rate}/s "
            f"(~{total_hosts / args.rate:.0f}s of launches)"
        )

    for subnet in subnets:
        ping_subnet(
            subnet,
            system,
            args.max_hosts,
            args.count,
            args.rate,
            shuffle=not args.in_order,
        )


if __name__ == "__main__":
    main()

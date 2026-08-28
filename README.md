[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
![GitHub language count](https://img.shields.io/github/languages/count/rikosintie/nmap-python)
![Twitter Follow](https://img.shields.io/twitter/follow/rikosintie?style=social)
[![Commit Activity](https://img.shields.io/github/commit-activity/m/rikosintie/Discovery)](https%3A%2F%2Fgithub.com%2Frikosintie%2FDiscovery)
[![Website](https://img.shields.io/badge/Works_with-Windows/MacOS/Linux-blue)](https://github.com/rikosintie/CookBook)
[![Website](https://img.shields.io/badge/Blog-Visit-blue)](https://mwhubbard.blogspot.com)
[![License](https://img.shields.io/github/license/rikosintie/Discovery?color=0096FF)](https://github.com/rikosintie/Discovery)
[![X](https://img.shields.io/twitter/follow/rikosintie?style=social&logo=x)](https://twitter.com/rikosintie)

----------------------------------------------------------------

# Warming the ARP cache with pinger.py

If you are pulling the ARP table from a switch, you need to refresh it before running the show command.
The port maps created by [config-pull.py](https://rikosintie.github.io/Discovery/intro/)
are only as complete as the ARP table, and a switch only has an ARP entry for a host that has sent
traffic recently.

`pinger.py` reads a list of subnets and pings every host
in them so the gateways learn all the endpoints before the discovery run.

Put the subnets in a file (the default is `vlans.txt`), one per line. You can
paste straight from a switch —

```text
show run | i ^interface|^ ip address
```

```
# paste this into vlans.txt
interface Vlan10
 ip address 10.20.10.1 255.255.255.0
interface Vlan20
 ip address 10.20.20.1 255.255.255.0
interface Vlan30
 ip address 10.20.30.1 255.255.255.0
```

— or list them as `address mask` or CIDR:

```text
# Access Controller VLAN
10.20.10.0 255.255.255.0
# BACnet VLAN
10.20.20.0/24
# Environmental Monitoring VLAN
10.20.30.0/24
```

Blank lines, lines containing `interface`, and lines starting with `#` are
ignored, so `#` comments out a subnet. Subnets larger than `-m/--max-hosts`
addresses (default 2100, i.e. bigger than a `/21`) are skipped.

```bash
python3 pinger.py
python3 pinger.py -f user-subnets.txt
```

## Cross-platform commands

"Linux"

```text
python3 pinger.py                                                                                                                                                   [11:36:18]

OS is Linux, sending 1 echo request per host
IP addresses have been randomized
Number of Subnets: 3
90 hosts to ping at 20/s (~4s of launches)

Pinging 30 hosts in 192.168.10.96/27
```

----------------------------------------------------------------

"macOS"

```text
python3 pinger.py

OS is Darwin, sending 1 echo request per host
IP addresses have been randomized
Number of Subnets: 3
90 hosts to ping at 20/s (~4s of launches)

Pinging 30 hosts in 192.168.10.96/27
```

----------------------------------------------------------------

"Windows"

```text
 python3 pinger.py -r 10

OS is Windows, sending 1 echo request per host
IP addresses have been randomized
Number of Subnets: 3
90 hosts to ping at 10/s (~9s of launches)

Pinging 30 hosts in 192.168.10.96/27
```

### Which subnets are worth pinging

Desktops, laptops, access points, IP phones, and surveillance cameras
send traffic all the time, so the switches already have a current ARP
entry for them. Pinging those subnets adds noise without adding much to
the port maps.

The devices that need warming up are the ones that sit quiet until
something talks to them:

- Door access controllers
- Building automation controllers (usually BACnet)
- Environmental monitoring systems (usually EMS)
- Any other IoT device that waits for instructions
- Printers set to auto sleep (not auto power off)

When these devices live on their own segmented VLANs, point `pinger.py` at
just those VLANs — there's no need to sweep the user subnets.

### Being gentle on EDR / NDR

Firing ICMP at every address in a subnet all at once looks exactly like a
horizontal scan and can get the machine running `pinger.py` alerted on or
quarantined at customers running CrowdStrike, SentinelOne, Darktrace, and
similar. Two arguments keep the sweep quiet:

- **`-r`, `--rate`** — the maximum number of pings started per second
  (default `20`). This is the setting that keeps the traffic looking like
  background noise instead of a scan. `--rate 0` removes the limit and
  starts every ping at once (the old, noisy behaviour).
- **`-c`, `--count`** — ICMP echo requests per host (default `1`). One
  request is enough to make the gateway learn the MAC; raise it only if
  you want more confidence that a host is really up.

Host order within each subnet is randomised by default (add `--in-order`
to disable). Before it starts, the script prints how many hosts it will
ping and roughly how long the launches will take at the chosen rate.

```bash
# One echo per host, 10 per second - light background traffic.
python3 pinger.py -r 10 -c 1
```

Even a paced sweep is quiet, not invisible — coordinate with the
customer's SOC first.

## Real-world example

I was tasked with replacing the core and edge switches for a customer. They had added a SCADA network that wasn't well documented, several HP/Ricoh printers that were mission-critical, three SANs, Ubiquiti wireless bridges connecting buildings and four VMware ESXi hosts. 

The edge switches didn't have port descriptions on most of the ports, and the patch cables going to the servers were zip-tied into several bundles. I wanted to document what device was on each port before replacing the switches so that I could compare afterwards and make sure everything was moved correctly.

Initially, I wrote a quick Python script that would convert the output of "show mac add inter x/x | i Gi" into an easy-to-read format showing only ports that had MAC addresses. The script also looks up the MAC address using the Wireshark OUI database and includes the NIC manufacturer. The script used to be a standalone tool; it's now one of the "Helper Scripts" in the Discovery project. You can grab that script here [Creating Port Maps](https://rikosintie.github.io/Discovery/Helper-scripts/#creating-port-maps). 

The problem with creating port maps is that if a device goes to sleep, the switch ARP table entry will time out and be discarded. Since I was doing the upgrade on a holiday, many devices had timed out. I had been thinking about writing a script to parse the SVI interfaces and then ping the hosts to refresh the MAC and ARP tables. This finally gave me the motivation to do it. 

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
![GitHub language count](https://img.shields.io/github/languages/count/rikosintie/nmap-python)
![Twitter Follow](https://img.shields.io/twitter/follow/rikosintie?style=social)

# Warming the ARP cache with pinger.py

The port maps are only as complete as the ARP tables `config-pull.py`
collects, and a switch only has an ARP entry for a host that has sent
traffic recently. `pinger.py` reads a list of subnets and pings every host
in them so the gateways learn all the endpoints before the discovery run.

Put the subnets in a file (default `vlans.txt`), one per line. You can
paste straight from a switch —

```text
show run | i ^interface|^ ip address

interface Vlan10
 ip address 10.20.10.1 255.255.255.0
```

— or list them as `address mask` or CIDR:

```text
10.20.10.0 255.255.255.0
10.20.20.0/24
```

Blank lines, lines containing `interface`, and lines starting with `#` are
ignored, so `#` comments a subnet out. Subnets larger than `-m/--max-hosts`
addresses (default 2100, i.e. bigger than a `/21`) are skipped.

```bash
python3 pinger.py
python3 pinger.py -f user-subnets.txt
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
- Any other IoT device that just waits for instructions

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

pingSVI
From sh run | i ^interface|^_ip address parses subnets and pings all host. Populates switch's arp table.

NOTE: This script works best on Linux/MAC. You can also use the Windows Subsystem for Linux. On Windows it returns "Active" even for hosts that don't exist. It still updates ARP table which is the purpose. If I get time, I will add the code need to make it work correcly on Windows. 

I use the Ubuntu 18.04 version but I would think any Linux subsystem would work. Microsoft has an [FAQ](https://docs.microsoft.com/en-us/windows/wsl/faq) on WSL.

I was tasked with replacing the core and edge switches for a customer. They had added a SCADA network which wasn't well documented and had many HP/Ricoh printers, three SANs, many Ubiquti wireless bridges connecting remote sites and four VWare ESXi hosts. 

The edge switches didn't have port descriptions on a lot of the ports and the patch cables going to the servers were zipped tied into several bundles. I wanted to document what device was on each port before replacing the switches so that I could compare afterwards and make sure everything was moved correctly.

Initially I wrote a quick Python script that would convert the ouput of "show mac add inter x/x | i Gi" into an easy to read format showing only ports that had MAC addresses. The script also looks up the MAC using the Wireshark OUI database and includes the manufacture of the NIC. You can grab that script here [Convert Interface MAC addresses to manufacturer name](https://github.com/rikosintie/MAC2Manuf). 

The problem here is that devices go to sleep and the switch times the mac address out of the table. Since I was doing the upgrade on a holiday, a lot of devices had timed out.  I had been thinking about writing a script to parse the SVI interfaces and then ping the hosts to refresh the MAC and arp tables. This finally gave me the motivation to do it. 

**Usage**

From the core switch run 

`show run | i ^interface|^_ip address` 

to output the SVIs and their subnets. The output will look like this:
```powershell
sh run | i ^interface|^_ip address
interface Vlan1
# ip address 10.23.128.129 255.255.255.248 secondary
# ip address 10.23.159.1 255.255.255.248 secondary
# ip address 10.132.0.1 255.255.255.248
 ip address 192.168.10.1 255.255.255.240
interface Vlan2
 ip address 10.132.2.1 255.255.255.248
interface Vlan4
# ip address 10.132.4.1 255.255.255.248
interface Vlan5
# ip address 10.23.129.1 255.255.255.248 secondary
 ip address 10.132.5.1 255.255.255.248
interface Vlan10
 ip address 10.132.10.1 255.255.255.248
 ```
Save this to a file named `vlans.txt` 

Linux is case sensitve so you must use all lowercase in the file name.
 
Run the script:
 `python3 pinger.py' 
 
It will do the following:
 ```
Read vlans.txt
Parse the file and drop blank lines and any lines that contain a # or the word interface. This allows you to comment out subnets that you don't want to ping
Print out the number of subnets found
Print out the hosts for each subnet
Ping the hosts
Print out "Active" for hosts that are alive and "no response" for hosts that don't respond.
```
Here is the output. I didn't have access to the customer's network when I ran this for documentation so all the hosts are "no response". The 192.168.10.0 subnet is my home lab.

```powershell
python3 pinger.py 


Number of Subnets: 3

Pinging hosts in Subnet  10.175.0.0/23

------ Results from the Pings ------
10.175.0.2 active
10.175.0.4 active
10.175.0.3 active
10.175.0.5 active
10.175.0.6 active
...

10.175.1.1 active
10.175.1.10 active
10.175.1.11 active
10.175.1.21 active
10.175.1.30 active
...

10.175.0.1 no response
10.175.0.39 no response
10.175.0.46 no response
10.175.1.0 no response
10.175.1.2 no response

...

Pinging hosts in Subnet  10.175.2.0/23

------ Results from the Pings ------
10.175.2.1 active
10.175.2.2 no response
10.175.2.3 no response
10.175.2.4 no response
...

10.175.3.254 no response

Pinging hosts in Subnet  10.175.4.0/24

------ Results from the Pings ------
10.175.4.1 active
10.175.4.2 no response
...

10.175.4.254 no response
```
Here is an "asciicinema" recording of the script in action:
[python3 pinger.py](https://asciinema.org/a/p9ICnD759vWOzvhJLPDxGMphY)

asciicinema is a cool little terminal recording tool. It can be found on github at
[asciicinema](https://github.com/asciinema/asciinema)

 

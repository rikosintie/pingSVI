# pingSVI
From sh run | i ^interface|^_ip address parses subnets and pings all host. Populates switch's arp table.

NOTE: This script only runs on Linux/MAC. I will try to add Windows support in the future.

I was tasked with replacing the core and edge switches for a government agency. They had added a SCADA network which wasn't well documented and had many HP/Ricoh printers, three SANs, many Ubiquti wireless bridges connecting remote sites and four VWare ESXi hosts. 

The edge switches didn't have port descriptions on a lot of the ports and the patch cables going to the servers were zipped tied into several bundles. I wanted to document what device was on each port before replacing the switches so that I could compare afterwards and make sure everything was moved correctly.

Initially I wrote a quick Python script that would convert the ouput of "show mac add inter x/x | i Gi" into an easy to read format showing only ports that had MAC addresses. The script also looks up the MAC using the Wireshark OUI database and includes the manufacture of the NIC. You can grab that script here [Convert Interface MAC addresses to manufacturer name](https://github.com/rikosintie/MAC2Manuf). 

The problem here is that devices go to sleep and the switch times the mac address out of the table. Since I was doing the upgrade on a holiday, a lot of devices had timed out.  I had been thinking about writing a script to parse the SVI interfaces and then ping the hosts to refresh the MAC and arp tables. This finally gave me the motivation to do it. 

#Usage

From the core switch run `show run | i ^interface|^_ip address` to output the SVIs and their subnets. The output will look like this:
```
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
Save this to a file named `vlans.txt`. Linux is case sensitve so you must use all lowercase in the file name.
 
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
Here is the output. I didn't have access to the customers network when I ran this for documentation so all the hosts are "no response". The 192.168.10.0 subnet is my home lab.

```
python3 pinger.py 

Number of Subnets: 4

Ping these hosts in Subnet  192.168.10.0/28
192.168.10.1
192.168.10.2
192.168.10.3
192.168.10.4
192.168.10.5
192.168.10.6
192.168.10.7
192.168.10.8
192.168.10.9
192.168.10.10
192.168.10.11
192.168.10.12
192.168.10.13
192.168.10.14

Ping these hosts in Subnet  10.132.2.0/29
10.132.2.1
10.132.2.2
10.132.2.3
10.132.2.4
10.132.2.5
10.132.2.6

Ping these hosts in Subnet  10.132.5.0/29
10.132.5.1
10.132.5.2
10.132.5.3
10.132.5.4
10.132.5.5
10.132.5.6

Ping these hosts in Subnet  10.132.10.0/29
10.132.10.1
10.132.10.2
10.132.10.3
10.132.10.4
10.132.10.5
10.132.10.6

***** Results from the Pings *****
192.168.10.3 active
192.168.10.5 active
192.168.10.10 active
192.168.10.13 active
192.168.10.1 no response
192.168.10.2 no response
192.168.10.4 no response
192.168.10.6 no response
192.168.10.7 no response
192.168.10.8 no response
192.168.10.9 no response
192.168.10.11 no response
192.168.10.12 no response
192.168.10.14 no response
10.132.2.1 no response
10.132.2.2 no response
10.132.2.3 no response
10.132.2.4 no response
10.132.2.5 no response
10.132.2.6 no response
10.132.5.1 no response
10.132.5.2 no response
10.132.5.3 no response
10.132.5.4 no response
10.132.5.5 no response
10.132.5.6 no response
10.132.10.1 no response
10.132.10.2 no response
10.132.10.3 no response
10.132.10.4 no response
10.132.10.5 no response
10.132.10.6 no response
```

 

#!/usr/bin/env python3
'''
References
https://www.tutorialspoint.com/python3/python_strings.htm
https://www.tutorialspoint.com/python3/python_lists.htm
https://stackoverflow.com/questions/12101239/multiple-ping-script-in-python/12102040#12102040
https://stackoverflow.com/questions/12101239/multiple-ping-script-in-python
https://docs.python.org/3/library/ipaddress.html
https://codereview.stackexchange.com/questions/145126/open-a-text-file-and-remove-any-blank-lines
https://www.tutorialspoint.com/python3/python_exceptions.htm
'''

import os
import time
import ipaddress
from subprocess import Popen, DEVNULL
print()
#create a blank list to hold the subnets
subnet_list = []
#read Vlans.txt and build a list of subnets
#create a blank list to accept each line in the file from Vlans.txt
data = []
try:
    f = open('vlans.txt', 'r')
except FileNotFoundError:
            print('vlans.txt does not exist')
else:    
#f = open('vlans.txt', 'r')
    for line in f:
#strip out empty lines
        if line.strip():
            data.append(line)
    f.close
ct = len(data)-1
counter = 0
while counter <= ct:
    IP = data[counter]
#    print('raw IP', IP)
#Remove Enter at end of line
    IP = IP.strip('\n')
#skip any line with with a # or interface. This allows you to comment out subnets
    if IP.find('interface') != -1 or IP.find('#') != -1:
        counter = counter + 1
        continue
    L = str.split(IP)
    snet = L[2]
    netmask = L[3]
    IP = snet + '/' + netmask
    subnet_list.append(IP)
    counter = counter + 1
ct = len(subnet_list)-1
counter = 0
if ct > 0:
    print('Number of Subnets:', ct + 1)
p = {} # ip -> process
while counter <= ct:
    IP = subnet_list[counter]    
    subnet = ipaddress.ip_network(IP, strict=False)
    print()
    print('Ping these hosts in Subnet ', subnet)
    for i in subnet.hosts():
        i = str(i)
        print(i)
        p[i] = Popen(['ping', '-n', '-w5', '-c3', i], stdout=DEVNULL)
    #NOTE: you could set stderr=subprocess.STDOUT to ignore stderr also
    counter = counter + 1
print()
print('***** Results from the Pings *****')

while p:
    for ip, proc in p.items():
        if proc.poll() is not None: # ping finished
            del p[ip] # remove from the process list
            if proc.returncode == 0:
                print('%s active' % ip)
            elif proc.returncode == 1:
                print('%s no response' % ip)
            else:
                print('%s error' % ip)
            break

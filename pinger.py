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

#  import os
#  import time
import ipaddress
import platform
from subprocess import Popen, DEVNULL, PIPE
import subprocess
import shlex
print()
#  platform_name = os.uname()
System_name = platform.system()
print('OS is ', System_name)

# create a blank list to hold the subnets
subnet_list = []
# read Vlans.txt and build a list of subnets
# create a blank list to accept each line in the file from Vlans.txt
data = []
try:
    f = open('vlans.txt', 'r')
except FileNotFoundError:
    print('vlans.txt does not exist')
else:
    for line in f:
        # strip out empty lines
        if line.strip():
            data.append(line)
    f.close
ct = len(data)-1
counter = 0
while counter <= ct:
    IP = data[counter]
#    print('raw IP', IP)
# Remove Enter at end of line
    IP = IP.strip('\n')
# skip any line with with a # or interface. Allows you to comment out subnets
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
p = {}  # ip -> process
while counter <= ct:
    IP = subnet_list[counter]
    subnet = ipaddress.ip_network(IP, strict=False)
    print()
# On large subnets >/21 the ping process fails. This if statement
# skips subnets with more than /21 hosts.
    if subnet.num_addresses < 2100:
        print('Pinging hosts in Subnet ', subnet)
        for i in subnet.hosts():
            i = str(i)
# to see all hosts that will be pinged uncomment the next line.
#            print(i)
#            p[i] = subprocess.Popen(['ping', '-n', '-w5', '-c3', i], stdout=DEVNULL, stderr=subprocess.STDOUT)
            #  ran in python 3.8.x
            if System_name == "Darwin" or System_name == "Linux":
                cmd = "ping -n -c 3 " + i
                args = shlex.split(cmd)
            else:
                cmd = "ping -n 3 " + i
                args = shlex.split(cmd)
                shell_needed = True
#                print("Args", args)
#  subprocess.run([cmd, cmd_args])
            p[i] = subprocess.Popen(args, stdout=subprocess.DEVNULL, \
                stderr=subprocess.STDOUT)

#            p[i] = subprocess.Popen(['ping', '-n', '-c3', i], stdout=DEVNULL, stderr=subprocess.STDOUT)
        # NOTE: you could set stderr=subprocess.STDOUT to ignore stderr also

        print()
        print('------ Results from the Pings ------')

        while p:
            for ip, proc in p.items():
                if proc.poll() is not None:  # ping finished
                    del p[ip]  # remove from the process list
#                    print(proc.returncode)
                    if proc.returncode == 0:
                        print('%s active' % ip)
                    elif proc.returncode != 0:
                        print('%s no response' % ip)
                    else:
                        print('%s error' % ip)
                        print('%s return' % proc.returncode)
                    break
        counter = counter + 1
    else:
        print('Skipped subnet ', subnet)
        counter += 1

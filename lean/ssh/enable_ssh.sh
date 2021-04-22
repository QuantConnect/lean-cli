#!/bin/sh
rm -f /etc/service/sshd/down
/usr/sbin/enable_insecure_key
chmod 600 /etc/insecure_key
echo "HostKey /etc/insecure_key" >> /etc/ssh/sshd_config

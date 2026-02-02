#!/bin/sh
apt update
apt install apache2 python3-uvicorn python3-fastapi python3-pip --assume-yes
pip install bmp280 --break-system-packages
cp pmpctrl.service /etc/systemd/system
systemctl enable pmpctrl.service
systemctl start pmpctrl.service
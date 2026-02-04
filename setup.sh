#!/bin/sh
apt update
apt install apache2 python3-uvicorn python3-fastapi python3-pip --assume-yes
pip install bmp280 --break-system-packages
wget -qO- https://github.com/KDxGP/PMPCTRL/releases/latest/download/PMPCTRL.tar.gz | gunzip | tar xvf - -C /opt
ln /opt/PMPCTRL/pmpctrl.service /etc/systemd/system
systemctl enable pmpctrl.service
systemctl start pmpctrl.service
wget -qO- https://github.com/KDxGP/PMPCTRL_UI/releases/latest/download/PMPCTRL_UI.tar.gz | gunzip | tar xvf - -C /var/www/html/
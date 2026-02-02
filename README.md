Style Guide
https://google.github.io/styleguide/pyguide.html

# Installation
1. Setup Pi SD card with image, configure WiFi and enable SSH
2. Enable I2C with `raspi-config` tool
3. clone repo into `/opt/PMPCTRL` (if not change `WorkingDirectory` in `pmpctrl.service` file)
4. run `rpi-setup.sh` as root/sudo
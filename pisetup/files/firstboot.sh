#!/bin/bash
# Script to run by root on first boot of the Pi

cd /home/pi/
git clone --single-branch --branch raspberrypi https://github.com/mvsoom/gedankenpolizei.git

# Setup environment for gedankenpolizei
cd gedankenpolizei
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Arial Unicode MS for very high diacritic towers
# https://askubuntu.com/questions/651441/how-to-install-arial-font-and-other-windows-fonts-in-ubuntu
# If fails, client will fall back to Arial
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | sudo debconf-set-selections
sudo apt-get install -y ttf-mscorefonts-installer
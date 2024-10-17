# Start x and run .xinitrc if on tty1 (autologin)
if [ -z $DISPLAY ] && [ $(tty) = /dev/tty1 ]
then
    startx
fi
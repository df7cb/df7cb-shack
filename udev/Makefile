install: /etc/udev/rules.d/shack.rules

/etc/udev/rules.d/shack.rules: shack.rules
	sudo install -m644 $< $@
	#sudo systemctl restart systemd-udevd
	sudo udevadm control --reload-rules

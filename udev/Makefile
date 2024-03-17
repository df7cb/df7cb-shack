UNITS = $(wildcard *.service *.socket *.path)
INSTALL_UNITS = $(patsubst %,$(HOME)/.config/systemd/user/%,$(UNITS))

install: /etc/udev/rules.d/shack.rules $(INSTALL_UNITS)
	systemctl --user daemon-reload

/etc/udev/rules.d/shack.rules: shack.rules
	sudo install -m644 $< $@
	#sudo systemctl restart systemd-udevd
	sudo udevadm control --reload-rules

$(HOME)/.config/systemd/user/%: %
	install -m644 $< $@

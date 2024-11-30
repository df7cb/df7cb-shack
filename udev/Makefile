UNITS = $(wildcard *.service *.socket *.path)
INSTALL_UNITS = $(patsubst %,$(HOME)/.config/systemd/user/%,$(UNITS))

install: /etc/udev/rules.d/shack.rules $(INSTALL_UNITS) $(HOME)/.config/wireplumber/wireplumber.conf.d/99-soundcards.conf
	systemctl --user daemon-reload

/etc/udev/rules.d/shack.rules: shack.rules
	sudo install -m644 $< $@
	sudo udevadm control --reload-rules

$(HOME)/.config/systemd/user/%: %
	install -m644 $< $@

# https://unix.stackexchange.com/a/772584/137160
$(HOME)/.config/wireplumber/wireplumber.conf.d/%: %
	mkdir -p $(basename $@)
	install -m644 $< $@
	systemctl --user restart wireplumber.service

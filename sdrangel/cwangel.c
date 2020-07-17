/*
 * listen to CW keyer input from an arduino on a USB port and forward to
 * sdrangel API
 *
 * Copyright (C) 2019-2020 Christoph Berg DF7CB <cb@df7cb.de>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 */

//#define BAUD 115200
#define BAUD 1200

#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <termios.h>
#include <ctype.h>

/*
 * error - wrapper for perror
 */
void error(char *msg)
{
	perror(msg);
	exit(1);
}

int main(int argc, char **argv)
{
	int keyerfd;
	struct termios settings;
	setlinebuf(stdout);

	if (argc != 2) {
		printf("Syntax: cwdaemon /dev/ttyACM0\n");
		exit(1);
	}

	do {
		keyerfd = open(argv[1], O_RDWR);
		if (keyerfd < 0) {
			if (errno == EBUSY) {
				perror(argv[1]);
				sleep(1);
			} else
				error(argv[1]);
		}
	} while (keyerfd < 0);

	tcgetattr(keyerfd, &settings);
	cfsetspeed(&settings, BAUD);
	cfmakeraw(&settings);
	tcsetattr(keyerfd, TCSANOW, &settings); /* apply the settings */
	tcflush(keyerfd, TCOFLUSH);

	printf("Connected to %s\n", argv[1]);

	int oldstate = -1; /* force off at start */
	int state = 0;

	/*
	 * main loop: wait for a datagram, then send it to keyer
	 */
	while (1) {
		fd_set fds;
		FD_ZERO(&fds);
		FD_SET(keyerfd, &fds);

		if (select(keyerfd + 1, &fds, NULL, NULL, NULL) < 0)
			error("select");
		if (FD_ISSET(keyerfd, &fds)) {
			char buf[100];
			int n = read(keyerfd, buf, sizeof(buf));
			if (n < 0)
				error("read");
			if (n == 0) {
				printf("Keyer disconnected\n");
				exit(0);
			}

			for (int i = 0; i < n; i++) {
				if (buf[i] == '^') {
					state = 1;
				} else if (buf[i] == '_') {
					state = 0;
				} else {
					write(1, buf+i, 1);
				}
			}
		}

		if (state != oldstate) {
		switch (state) {
			case 0:
				system("curl -X PATCH --data @settings.0 http://127.0.0.1:8091/sdrangel/deviceset/1/channel/0/settings");
				break;
			case 1:
				system("curl -X PATCH --data @settings.1 http://127.0.0.1:8091/sdrangel/deviceset/1/channel/0/settings");
				break;
		}
		state = oldstate;
		}
	}
}

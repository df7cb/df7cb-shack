/*
 * listen to CW keyer input from an arduino on a USB port and forward to
 * sdrangel API
 *
 * Copyright (C) 2019-2021 Christoph Berg DF7CB <cb@df7cb.de>
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
//#define PORTNO 6789
#define PORTNO 6790
#define BUFSIZE 1024

#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <termios.h>
#include <ctype.h>
#include <curl/curl.h>

#define JSONAPI "http://127.0.0.1:8091/sdrangel/deviceset/1/channel/0/settings"
#define JSONTEMPLATE "{ \"SSBModSettings\": { \"modAFInput\": %d }, \"channelType\": \"SSBMod\", \"direction\": 1}"

/*
 * error - wrapper for perror
 */
void error(char *msg)
{
	perror(msg);
	exit(1);
}

size_t
fdiscard (char *ptr, size_t size, size_t nmemb, void *userdata)
{
	return nmemb;
}

/*
 * curl -X PATCH --data @settings.0 http://127.0.0.1:8091/sdrangel/deviceset/1/channel/0/settings
 */
void
key_up_down (int state)
{
	CURLcode ret;
	static CURL *hnd = NULL;
	char request[sizeof(JSONTEMPLATE)];

	sprintf(request, JSONTEMPLATE, state);

	if (! hnd)
		hnd = curl_easy_init();

	curl_easy_setopt(hnd, CURLOPT_BUFFERSIZE, 102400L);
	curl_easy_setopt(hnd, CURLOPT_URL, JSONAPI);
	curl_easy_setopt(hnd, CURLOPT_NOPROGRESS, 1L);
	curl_easy_setopt(hnd, CURLOPT_POSTFIELDS, request);
	curl_easy_setopt(hnd, CURLOPT_POSTFIELDSIZE_LARGE, (curl_off_t)strlen(request));
	curl_easy_setopt(hnd, CURLOPT_USERAGENT, "curl/7.68.0");
	curl_easy_setopt(hnd, CURLOPT_MAXREDIRS, 50L);
	curl_easy_setopt(hnd, CURLOPT_HTTP_VERSION, (long)CURL_HTTP_VERSION_2TLS);
	curl_easy_setopt(hnd, CURLOPT_CUSTOMREQUEST, "PATCH");
	curl_easy_setopt(hnd, CURLOPT_TCP_KEEPALIVE, 1L);
	curl_easy_setopt(hnd, CURLOPT_WRITEFUNCTION, fdiscard); /* discard response body */

	ret = curl_easy_perform(hnd);
	if (ret != CURLE_OK)
		error("curl");
	//printf("CW %i\n", state);
}

int setup_cwdaemon()
{
	int sockfd;		/* socket */
	struct sockaddr_in serveraddr;	/* server's addr */
	int optval;		/* flag value for setsockopt */

	/*
	 * socket: create the parent socket
	 */
	sockfd = socket(AF_INET, SOCK_DGRAM, 0);
	if (sockfd < 0)
		error("ERROR opening socket");

	/* setsockopt: Handy debugging trick that lets
	 * us rerun the server immediately after we kill it;
	 * otherwise we have to wait about 20 secs.
	 * Eliminates "ERROR on binding: Address already in use" error.
	 */
	optval = 1;
	setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR,
		   (const void *)&optval, sizeof(int));

	/*
	 * build the server's Internet address
	 */
	bzero((char *)&serveraddr, sizeof(serveraddr));
	serveraddr.sin_family = AF_INET;
	serveraddr.sin_addr.s_addr = htonl(INADDR_ANY);
	serveraddr.sin_port = htons((unsigned short)PORTNO);

	/*
	 * bind: associate the parent socket with a port
	 */
	if (bind(sockfd, (struct sockaddr *)&serveraddr,
		 sizeof(serveraddr)) < 0)
		error("ERROR on binding");
	printf("Listening on :%d\n", PORTNO);

	return sockfd;
}

void
read_cwdaemon(int sockfd, int keyerfd)
{
	char buf[BUFSIZE];	/* message buf */
	int n;			/* message byte size */

	n = recv(sockfd, buf, BUFSIZE-1, 0);
	if (n < 0)
		error("ERROR in recvfrom");
	if (n == 0) /* skip empty packets */
		return;

#if 0
	if (buf[0] == '\033') {
		switch (buf[1]) {
			case '4': /* abort current message */
				break;
			default:
				buf[n] = '\0';
				printf("Unknown ESC message: %s\n", buf + 1);
				break;
		}
		return;
	}
#endif

	buf[n] = '\0';
	if (n > 1 && buf[n-1] == '\n')
		buf[n-1] = '\0';

	for (int i = 0; i < n; i++) {
		if (buf[i] == '\0')
			return;
		write(keyerfd, buf + i, 1);
		//printf("Sending %c\n", buf[i]);
	}
}

int main(int argc, char **argv)
{
	char *device;
	int keyerfd;
	int sockfd;
	struct termios settings;
	setlinebuf(stdout);

	if (argc == 1) {
		device = "/dev/ttyUSB0";
	} else if (argc == 2) {
		device = argv[1];
	} else {
		printf("Syntax: cwdaemon /dev/ttyACM0\n");
		exit(1);
	}

	do {
		keyerfd = open(device, O_RDWR);
		if (keyerfd < 0) {
			if (errno == EBUSY) {
				perror(device);
				sleep(1);
			} else
				error(device);
		}
	} while (keyerfd < 0);

	tcgetattr(keyerfd, &settings);
	cfsetspeed(&settings, BAUD);
	cfmakeraw(&settings);
	tcsetattr(keyerfd, TCSANOW, &settings); /* apply the settings */
	tcflush(keyerfd, TCOFLUSH);

	printf("Connected to %s, sending requests to %s\n", device, JSONAPI);

	sockfd = setup_cwdaemon();

	int oldstate = -1; /* force off at start */
	int state = 0;

	/*
	 * main loop: wait for a datagram, then send it to keyer
	 */
	while (1) {
		fd_set fds;
		FD_ZERO(&fds);
		FD_SET(keyerfd, &fds);
		FD_SET(sockfd, &fds);

		if (select(sockfd + 1, &fds, NULL, NULL, NULL) < 0)
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
			key_up_down (state);
			state = oldstate;
		}

		if (FD_ISSET(sockfd, &fds)) {
			read_cwdaemon(sockfd, keyerfd);
		}
	}
}

/*
 * CW keyer frontend for https://github.com/df7cb/df7cb-shack/tree/master/digispark_keyer
 * Compatible with cwdaemon
 *
 * Copyright (C) 2019-2020 Christoph Berg DF7CB <cb@df7cb.de>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the “Software”), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 * Inspired from: https://gist.github.com/miekg/a61d55a8ec6560ad6c4a2747b21e6128
 * udpserver.c - A simple UDP echo server
 */

#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <netdb.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <ctype.h>

#define DEBUG 1
#define BUFSIZE 1024
#define PORTNO 6789
#define DELAY 5000 /* sleep 5ms between signals. keep short so using the paddles to abort sending works */

static char *morse_char(char c) {
  switch (toupper(c)) {
    case '\n': /* fallthrough to space */
    case ' ': return " ";
    case 'A': return ".- ";
    case 'B': return "-... ";
    case 'C': return "-.-. ";
    case 'D': return "-.. ";
    case 'E': return ". ";
    case 'F': return "..-. ";
    case 'G': return "--. ";
    case 'H': return ".... ";
    case 'I': return ".. ";
    case 'J': return ".--- ";
    case 'K': return "-.- ";
    case 'L': return ".-.. ";
    case 'M': return "-- ";
    case 'N': return "-. ";
    case 'O': return "--- ";
    case 'P': return ".--. ";
    case 'Q': return "--.- ";
    case 'R': return ".-. ";
    case 'S': return "... ";
    case 'T': return "- ";
    case 'U': return "..- ";
    case 'V': return "...- ";
    case 'W': return ".-- ";
    case 'X': return "-..- ";
    case 'Y': return "-.-- ";
    case 'Z': return "--.. ";
    case '0': return "----- ";
    case '1': return ".---- ";
    case '2': return "..--- ";
    case '3': return "...-- ";
    case '4': return "....- ";
    case '5': return "..... ";
    case '6': return "-.... ";
    case '7': return "--... ";
    case '8': return "---.. ";
    case '9': return "----. ";
    case '+': return ".-.-. ";
    case ',': return "--..-- ";
    case '-': return "-....- ";
    case '.': return ".-.-.- ";
    case '/': return "-..-. ";
    case ';': return "---... ";
    case '=': return "-...- ";
    case '?': return "..--.. ";
    case '@': return ".--.-. ";
    case '*': return "*"; /* reset queue */
    default: return NULL;
  }
}

/*
 * error - wrapper for perror
 */
void error(char *msg)
{
	perror(msg);
	exit(1);
}

static void
read_char(unsigned char c)
{
	static int c0 = -1;

	if (c0 != -1) {
		printf("Speed is %d (%d %d)\n", 256*c0 + c, c0, c);
		c0 = -1;
		return;
	}

	switch (c) {
		case 0:
		case 1:
			printf("%d\n", c);
			break;
		case 2:
		case 3:
			c0 = c;
			break;
		default:
			printf("Unexpected char %d (c0 %d)\n", c, c0);
	}
}

void
read_digispark(int ttyfd)
{
	char buf[BUFSIZE];
	int n;

	n = read(ttyfd, buf, BUFSIZE);
	if (n < 0)
		error("read");
	if (n == 0) {
		printf("Digispark disconnected\n");
		exit(0);
	}

	buf[n] = '\0';
	for (int i = 0; i < n; i++)
		read_char(buf[i]);
}

void
send_cw(int sockfd, int ttyfd)
{
	char buf[BUFSIZE];	/* message buf */
	int n;			/* message byte size */

	if (sockfd == 0)
		n = read(sockfd, buf, BUFSIZE-1);
	else
		n = recv(sockfd, buf, BUFSIZE-1, 0);
	if (n < 0)
		error("ERROR in recvfrom");
	if (n == 0) /* skip empty packets */
		return;

	if (buf[0] == '\033') {
		switch (buf[1]) {
			case '4': /* abort current message */
				if (DEBUG) printf("Abort\n");
				if (write(ttyfd, "*", 1) != 1)
					error("write");
				break;
			default:
				buf[n] = '\0';
				printf("Unknown ESC message: %s\n", buf + 1);
				break;
		}
		return;
	}

	buf[n] = '\0';
	if (n > 1 && buf[n-1] == '\n')
		buf[n-1] = '\0';
	if (DEBUG) printf("Sending '%s'\n", buf);

	for (int i = 0; i < n; i++) {
		if (buf[i] == '\0')
			return;
		//write(1, buf + i, 1);
		char *code = morse_char(buf[i]);
		if (code) {
			for (int j = 0; code[j]; j++) {
				//write(1, code + j, 1);
				if (write(ttyfd, code + j, 1) != 1)
					error("write");
				usleep(DELAY);
			}
		} else {
			printf("Unknown symbol, cannot send: '%c'\n", buf[i]);
		}
	}
	if (DEBUG) printf("Done with '%s'\n", buf);
}

int main(int argc, char **argv)
{
	int sockfd;		/* socket */
	int ttyfd;
	struct sockaddr_in serveraddr;	/* server's addr */
	int optval;		/* flag value for setsockopt */

	setlinebuf(stdout);

	if (argc != 2) {
		printf("Syntax: cwdaemon /dev/ttyACM0\n");
		exit(1);
	}

	do {
		ttyfd = open(argv[1], O_RDWR);
		if (ttyfd < 0) {
			if (errno == EBUSY) {
				perror(argv[1]);
				sleep(1);
			} else
				error(argv[1]);
		}
	} while (ttyfd < 0);
	printf("Connected to %s\n", argv[1]);

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

	/*
	 * main loop: wait for a datagram, then send it to keyer
	 */
	while (1) {
		fd_set fds;
		FD_ZERO(&fds);
		FD_SET(ttyfd, &fds);
		//FD_SET(0, &fds);
		FD_SET(sockfd, &fds);

		if (select(sockfd + 1, &fds, NULL, NULL, NULL) < 0)
			error("select");
		if (FD_ISSET(ttyfd, &fds))
			read_digispark(ttyfd);
		//if (FD_ISSET(0, &fds))
		//	send_cw(0, ttyfd);
		if (FD_ISSET(sockfd, &fds))
			send_cw(sockfd, ttyfd);
	}
}

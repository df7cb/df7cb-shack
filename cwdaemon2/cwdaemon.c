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
 */

#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <termios.h>
#include <ctype.h>
#include <math.h> /* sin */
#include "pulse/simple.h"
#include "pulse/error.h"

#define BUFSIZE 1024

#define SILENCE 0		/* Waveforms for the tone generator */
#define SINE 1
#define SAWTOOTH 2
#define SQUARE 3

static int freq=800;					/* current cw sidetone freq */
long samplerate=44100;
static double edge=2.0;						/* rise/fall time in milliseconds */
int fulldotlen, dotlen, dashlen, charspeed;
int ed;							/* risetime, normalized to samplerate */
static int sound_buf[882000];  /* 20 second max buffer */
static int sound_bufpos = 0;
pa_simple *dsp_fd;

/*
 * error - wrapper for perror
 */
void error(char *msg)
{
	perror(msg);
	exit(1);
}

pa_simple *open_dsp () {
	/* The Sample format to use */
	static pa_sample_spec ss = {
		.format = PA_SAMPLE_S16LE,
		.rate = 8000,
		.channels = 1
	};
	ss.rate = samplerate;
	pa_simple *s = NULL;
	int error;

	if (!(s = pa_simple_new(NULL, "cwdaemon", PA_STREAM_PLAYBACK, NULL,
				"playback", &ss, NULL, NULL, &error))) {
	        fprintf(stderr, "pa_simple_new() failed: %s\n", 
				pa_strerror(error));
		exit(1);
	}
	return s;
}


/* tonegen generates a sinus tone of frequency 'freq' and length 'len' (samples)
 * based on 'samplerate', 'edge' (rise/falltime) */

static int tonegen (int freq, int len, int waveform) {
	int x=0;
	int out;
	double val=0;
	int e;

	for (x=0; x < len-1; x++) {
		switch (waveform) {
			case SINE:
				val = sin(2*M_PI*freq*x/samplerate);
				break;
			case SAWTOOTH:
				val=((1.0*freq*x/samplerate)-floor(1.0*freq*x/samplerate))-0.5;
				break;
			case SQUARE:
				val = ceil(sin(2*M_PI*freq*x/samplerate))-0.5;
				break;
			case SILENCE:
				val = 0;
		}


		if (x < ed) { val *= pow(sin(M_PI*x/(2.0*ed)),2); }	/* rising edge */

		if (x > (len-ed)) {								/* falling edge */
				val *= pow(sin(2*M_PI*(x-(len-ed)+ed)/(4*ed)),2); 
		}
		
		out = (int) (val * 32500.0);
		sound_buf[sound_bufpos++] = out;
	}
	pa_simple_write(dsp_fd, sound_buf, sound_bufpos*sizeof(short int), &e);
	sound_bufpos = 0;
	return 0;
}

void close_audio (void *s) {
	int e;
	pa_simple_drain(s, &e);
}


void
read_keyer(int keyerfd)
{
	char buf[BUFSIZE];
	int n;
	int waveform = SINE;

	n = read(keyerfd, buf, 1);
	if (n < 0)
		error("read");
	if (n == 0) {
		printf("Keyer disconnected\n");
		exit(0);
	}

	write(1, buf, 1);

	if (buf[0] == '^') {
		tonegen(freq, dotlen + ed, waveform);
		tonegen(0, fulldotlen - ed, SILENCE);
	} else if (buf[0] == '2') {
		tonegen(freq, dashlen + ed, waveform);
		tonegen(0, fulldotlen - ed, SILENCE);
	}
	//write_audio(dsp_fd, &full_buf[0], full_bufpos);
	close_audio(dsp_fd);
}

int main(int argc, char **argv)
{
	int keyerfd;
	struct termios settings;
	setlinebuf(stdout);
	speed_t baud = 115200;

	dsp_fd = open_dsp();
	charspeed = 120;
	ed = (int) (samplerate * (edge/1000.0));
	dotlen = (int) (samplerate * 6/charspeed);
	fulldotlen = dotlen;
	dashlen = 3*dotlen;

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
	cfsetspeed(&settings, baud);
	cfmakeraw(&settings);
	//settings.c_cflag &= ~PARENB; /* no parity */
	//settings.c_cflag &= ~CSTOPB; /* 1 stop bit */
	//settings.c_cflag &= ~CSIZE;
	//settings.c_cflag |= CS8 | CLOCAL; /* 8 bits */
	//settings.c_lflag = ~ICANON; /* canonical mode */
	//settings.c_oflag &= ~OPOST; /* raw output */
	tcsetattr(keyerfd, TCSANOW, &settings); /* apply the settings */
	tcflush(keyerfd, TCOFLUSH);

	printf("Connected to %s\n", argv[1]);

	/*
	 * main loop: wait for a datagram, then send it to keyer
	 */
	while (1) {
		fd_set fds;
		FD_ZERO(&fds);
		FD_SET(keyerfd, &fds);

		if (select(keyerfd + 1, &fds, NULL, NULL, NULL) < 0)
			error("select");
		if (FD_ISSET(keyerfd, &fds))
			read_keyer(keyerfd);
	}
}

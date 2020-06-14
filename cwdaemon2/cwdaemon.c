/*
 * CW tone generator listening to keyer input from an arduino on a USB port
 * Copyright (C) 2019-2020 Christoph Berg DF7CB <cb@df7cb.de>
 *
 * Pulseaudio routines adapted from qrq
 * Copyright (C) 2011  Fabian Kurz, DJ1YFK
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
static short int sound_buf[882000];  /* 20 second max buffer */
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

		if (x > (len-ed)) {					/* falling edge */
				val *= pow(sin(2*M_PI*(x-(len-ed)+ed)/(4*ed)),2); 
		}
		
		out = (int) (val * 32500.0);
		sound_buf[sound_bufpos++] = out;
	}
	pa_simple_write(dsp_fd, sound_buf, sound_bufpos*sizeof(short int), &e);
	sound_bufpos = 0;
	pa_simple_drain(dsp_fd, &e);
	return 0;
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
	tcsetattr(keyerfd, TCSANOW, &settings); /* apply the settings */
	tcflush(keyerfd, TCOFLUSH);

	printf("Connected to %s\n", argv[1]);

	int state = 0;

	/*
	 * main loop: wait for a datagram, then send it to keyer
	 */
	while (1) {
		fd_set fds;
		FD_ZERO(&fds);
		FD_SET(keyerfd, &fds);

		if (select(keyerfd + 1, &fds, NULL, NULL, 0) < 0)
			error("select");
		if (FD_ISSET(keyerfd, &fds)) {
			char buf[10];
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

		switch (state) {
			case 0:
				tonegen(0, dotlen - ed, SILENCE);
				break;
			case 1:
				tonegen(freq, dotlen + ed, SINE);
				break;
		}
	}
}

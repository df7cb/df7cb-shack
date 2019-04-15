/*
 * CW keyer for Digispark
 *
 * Works as standalone CW keyer, speed is adjusted via a potentiometer.
 * Listens on USB for raw dashes and dots ('-', '.', ' ').
 * cwdaemon compatible frontend driver is
 * https://github.com/df7cb/df7cb-shack/tree/master/cwdaemon
 *
 * Copyright (C) 2019 Christoph Berg DF7CB <cb@df7cb.de>
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

#include <DigiCDC.h>

#define DIT 0 // P0 dit input from paddle
#define DAH 2 // P2 dah input from paddle
#define KEY 1 // P1 output to rig (also on-board LED)
#define SPEED 0 // P5 analog input from 10k potentiometer as voltage divider; extra 27k series resistor to restrict input to >> 2.5V (otherwise digispark resets)

#define DAH_WEIGHT 2.5
#define PAUSE_WEIGHT 2.0
#define STEP 2 // delay() granularity

char send[100];
char *send_ptr;
int duration;
volatile int state = 0;

void setup() {
  SerialUSB.begin();
  pinMode(DIT, INPUT_PULLUP);
  pinMode(DAH, INPUT_PULLUP);
  pinMode(KEY, OUTPUT);
  char *send = '\0';
  send_ptr = send;
}

static inline bool dit_press() {
  return !digitalRead(DIT);
}

static inline bool dah_press() {
  return !digitalRead(DAH);
}

static inline int get_duration() {
  return (1120 - analogRead(SPEED)) / 8;
}

static void get_usb()
{
  while (SerialUSB.available()) {
    char input = SerialUSB.read();
    if (input == '*') { /* reset queue */
      *send = '\0';
      send_ptr = send;
      break;
    }
    *send_ptr = input;
    send_ptr++;
  }
}

static inline void wait(int duration) {
  SerialUSB.delay(duration);
}

static void send_symbol(int level, int duration, int dit_state, int dah_state)
{
  int i;
  digitalWrite(KEY, level);
  for (i = 0; i < duration; i += STEP) {
    wait(STEP);
    get_usb();
    if (dit_state && dit_press())
      state = dit_state;
    if (dah_state && dah_press())
      state = dah_state;
  }
}

void loop() {
  while(1) {
    duration = get_duration();

    switch (state) {

      case 0: /* start, clear send queue */
        digitalWrite(KEY, LOW);
        *send = '\0';
        send_ptr = send;
        state = 100; /* go to main loop */
        break;

      case 100: /* main loop */
        wait(STEP);
        get_usb();
        if (dit_press())
          state = 1;
        else if (dah_press())
          state = 2;
        if (*send)
          state = 10;

        break;

      case 1: /* dit */
        state = 3; /* go to pause after dit */
        send_symbol(HIGH, duration, 0, 6); /* go to pause before dah */
        break;

      case 2: /* dah */
        state = 4; /* go to pause after dah */
        send_symbol(HIGH, 3*duration, 5, 0); /* go to pause before dit */
        break;

      case 3: /* pause after dit */
        state = 0; /* go to idle */
        send_symbol(LOW, duration, 0, 2); /* go to dah */
        break;

      case 4: /* pause after dah */
        state = 0; /* go to idle */
        send_symbol(LOW, duration, 1, 0); /* go to dit */
        break;

      case 5: /* pause before dit */
        state = 1; /* go to dit */
        send_symbol(LOW, duration, 1, 0); /* still go to dit */
        break;

      case 6: /* pause before dah */
        state = 2; /* go to dah */
        send_symbol(LOW, duration, 2, 0); /* still go to dah */
        break;

      case 10: /* USB loop */
        if (!*send) {
          state = 11;
          break;
        }

        switch (*send) {
          case '.':
            send_symbol(HIGH, duration, 11, 11);
            if (state != 11)
              send_symbol(LOW, duration, 11, 11);
            break;
          case '-':
            send_symbol(HIGH, DAH_WEIGHT * duration, 11, 11);
            if (state != 11)
              send_symbol(LOW, duration, 11, 11);
            break;
          case ' ':
            send_symbol(LOW, PAUSE_WEIGHT * duration, 11, 11);
            break;
          /* ignore all other symbols */
        }

        for (int i = 0; send[i+1]; i++) {
          send[i] = send[i+1]; /* shift array left */
        }
        send_ptr--;
        *send_ptr = '\0';

        break;

      case 11: /* cancel USB operation */
        digitalWrite(KEY, LOW);
        while (dit_press() || dah_press()) {
          wait(STEP);
          get_usb();
        }
        state = 0;
        break;

    }
  }
}

/*
 * CW keyer for Digispark
 *
 * Board: "Digispark (Default - 16.5mhz)"
 *
 * Copyright (C) 2022 Christoph Berg DF7CB <cb@df7cb.de>
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

// cd ~/Arduino/libraries/
// git clone https://github.com/heartscrytech/DigisparkMIDI

#include <DigiMIDI.h>

DigiMIDIDevice midi;

#define PIN_DIT 0 // P0 dit input from paddle
#define PIN_LED 1  // Digispark model A onboard LED
#define PIN_DAH 2 // P2 dah input from paddle
//#define PIN_KEY 1 // P1 output to rig (also on-board LED)
#define PIN_SPEED 0 // P5 analog input from 10k potentiometer as voltage divider; extra 27k series resistor to restrict input to >> 2.5V (otherwise digispark resets)

#define NOTE_DIT 1
#define NOTE_DAH 2
#define CHANNEL_SPEED 3

int dit_pressed = 0;
int dah_pressed = 0;
int old_speed = 0;
int old_speed_value = 0;
#define THRESHOLD 7

static inline bool read_dit() {
  return !digitalRead(PIN_DIT);
}

static inline bool read_dah() {
  return !digitalRead(PIN_DAH);
}

static inline int read_speed_value() {
  return analogRead(PIN_SPEED); /* 756 .. 1020 */
}

void setup() {
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_DIT, INPUT_PULLUP);
  pinMode(PIN_DAH, INPUT_PULLUP);
  //pinMode(PIN_KEY, OUTPUT);
}

void loop() {
  int dit = read_dit();
  int dah = read_dah();
  int speed_value = read_speed_value();

  if (dit != dit_pressed) {
    if (dit)
      midi.sendNoteOn(NOTE_DIT, 1);
    else
      midi.sendNoteOff(NOTE_DIT, 0);
    dit_pressed = dit;
  }
  if (dah != dah_pressed) {
    if (dah)
      midi.sendNoteOn(NOTE_DAH, 1);
    else
      midi.sendNoteOff(NOTE_DAH, 0);
    dah_pressed = dah;
  }
  digitalWrite(PIN_LED, dit||dah ? HIGH : LOW);

  if (speed_value < old_speed_value-THRESHOLD || speed_value > old_speed_value+THRESHOLD) {
    int new_speed = (speed_value - 700) / 8;
    if (new_speed != old_speed)
      midi.sendControlChange(CHANNEL_SPEED, new_speed);
      old_speed = new_speed;
    old_speed_value = speed_value;
  }

  midi.update();
  midi.delay(10);
}

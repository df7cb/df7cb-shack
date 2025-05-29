#!/usr/bin/python3

# CW keyer with MIDI input, PulseAudio output
#
# Copyright (C) 2022, 2025 Christoph Berg DF7CB <cb@df7cb.de>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import mido
import time
import pasimple
from itertools import chain
from ctypes import c_uint8

import math
import os

# constants
sample_rate = 48000.0
ramp = 12 # at least 6ms ramp up/down (CWops recommendation)
freq = 850.0
volume = 100
default_wpm = 24

# global variables
dah_sample = None
dit_sample = None
dot_duration = None

morse = {
    ".-":     'A',
    ".-.-":   'Ä',
    "-...":   'B',
    "-.-.":   'C',
    "----":   'CH',
    "-..":    'D',
    ".":      'E',
    "..-.":   'F',
    "--.":    'G',
    "....":   'H',
    "..":     'I',
    ".---":   'J',
    "-.-":    'K',
    ".-..":   'L',
    "--":     'M',
    "-.":     'N',
    "---":    'O',
    "---.":   'Ö',
    ".--.":   'P',
    "--.-":   'Q',
    ".-.":    'R',
    "...":    'S',
    "-":      'T',
    "..-":    'U',
    "..--":   'Ü',
    "...-":   'V',
    ".--":    'W',
    "-..-":   'X',
    "-.--":   'Y',
    "--..":   'Z',
    "-----":  '0',
    ".----":  '1',
    "..---":  '2',
    "...--":  '3',
    "....-":  '4',
    ".....":  '5',
    "-....":  '6',
    "--...":  '7',
    "---..":  '8',
    "----.":  '9',
    ".-.-.":  '+',
    "--..--": ',',
    "-....-": '-',
    ".-.-.-": '.',
    "-..-.":  '/',
    "---...": ';',
    "-...-":  '=',
    "..--..": '?',
    ".--.-.": '@',
    ".-...":  '<AS>',
    "...-.-": '<SK>',
}

def erase_chars(chars):
    print('\010' * chars + ' ' * chars + '\010' * chars, end='')

def generate_sample(duration):
    """Generate a sine wave sample of duration+ramp ms"""

    ramp_samples = int(ramp / 1000.0 * sample_rate)
    num_samples = int((duration+ramp) / 1000.0 * sample_rate)

    audio = []
    for x in range(ramp_samples):
        audio.append(128+int(volume
                * 0.5 * (1 - math.cos(math.pi * x / ramp_samples)) # cosine ramp up
                * math.sin(2 * math.pi * freq * ( x / sample_rate ))))

    for x in range(ramp_samples, num_samples):
        audio.append(128+int(volume * math.sin(2 * math.pi * freq * ( x / sample_rate ))))

    for x in range(ramp_samples):
        audio.append(128+int(volume
                * 0.5 * (1 + math.cos(math.pi * x / ramp_samples)) # cosine ramp down
                * math.sin(2 * math.pi * freq * ((x+num_samples) / sample_rate))))

    return (c_uint8 * len(audio))(*audio)

def upload_samples(speed):
    dot_duration_ms = int(1200 / speed)
    dah_duration_ms = 3 * dot_duration_ms

    global dot_duration, dit_sample, dah_sample
    dot_duration = dot_duration_ms / 1000
    dit_sample = generate_sample(dot_duration_ms)
    dah_sample = generate_sample(dah_duration_ms)

def play_samples(pa, sample):
    for device in pa:
        device.write(sample)

def poll(midiport, paddles, blocking=False):
    dit, dah = paddles[1], paddles[2]

    if blocking:
        msgs = chain([midiport.receive()], midiport.iter_pending())
    else:
        msgs = midiport.iter_pending()

    for msg in msgs:
        #print(msg)
        if msg.type == 'note_on':
            if msg.note == 1:
                dit = True
            elif msg.note == 2:
                dah = True
        if msg.type in ('note_on', 'note_off') and msg.note in (1, 2):
            paddles[msg.note] = msg.type == 'note_on'

        if msg.type == 'control_change' and msg.control == 3:
            print(f"<{msg.value}>", end='', flush=True)
            upload_samples(msg.value)

    # return True if paddle was pressed or held during this polling period
    return dit, dah

def loop(midiport, pa, paddles):
    state = 'idle'
    sign = '' # character keyed
    sign_len = 0 # size of partial character printed so far

    while True:

        # play sample (asynchronously) for state
        if state == 'dit':
            print('.', end='', flush=True)
            sign += '.'
            sign_len += 1
            play_samples(pa, dit_sample)
        elif state == 'dah':
            print('-', end='', flush=True)
            sign += '-'
            sign_len += 1
            play_samples(pa, dah_sample)

        # sleep for state
        if state == 'idle':
            pass
        elif state == 'dah':
            time.sleep(3 * dot_duration)
        else:
            time.sleep(dot_duration)

        # read paddle input
        dit, dah = poll(midiport, paddles, False)

        # compute next state
        if state == 'idle':
            if dit:
                state = 'dit'
            elif dah:
                state = 'dah'
            else:

                # when idle, decode character keyed
                if sign in morse:
                    erase_chars(sign_len)
                    print(morse[sign], end='', flush=True)
                    sign_len = len(morse[sign])
                # if we can't decode it, append a space
                else:
                    print(' ', end='', flush=True)
                    sign_len += 1

                # poll again for paddle input
                ts = time.time()
                dit, dah = poll(midiport, paddles, True)
                delay = time.time() - ts

                # if the delay was short enough, the last character was continued
                if delay <= dot_duration and (dit or dah):
                    # last character is continued
                    erase_chars(sign_len)
                    print(sign, end='', flush=True)
                    sign_len = len(sign)
                # otherwise, start a new character or a new word
                else:
                    if delay >= 5 * dot_duration:
                        print(' ', end='', flush=True)
                    sign = ''
                    sign_len = 0

        elif state == 'pause before dit':
            state = 'dit'

        elif state == 'pause before dah':
            state = 'dah'

        elif state == 'dit':
            if dah:
                state = 'pause before dah'
            else:
                state = 'pause after dit'

        elif state == 'dah':
            if dit:
                state = 'pause before dit'
            else:
                state = 'pause after dah'

        elif state == 'pause after dit':
            if dah:
                state = 'dah'
            else:
                state = 'idle'

        elif state == 'pause after dah':
            if dit:
                state = 'dit'
            else:
                state = 'idle'

        else:
            raise Exception("Bad state")

def main():
    midiport = mido.open_input('MidiStomp MIDI 1')
    midiport.iter_pending() # drain pending notes

    pa = [
            # side tone channel (default device)
            pasimple.PaSimple(pasimple.PA_STREAM_PLAYBACK,
                              pasimple.PA_SAMPLE_U8,
                              1,
                              int(sample_rate),
                              app_name='midicw',
                              stream_name='sidetone'),
            # TX tone channel (tx0)
            pasimple.PaSimple(pasimple.PA_STREAM_PLAYBACK,
                              pasimple.PA_SAMPLE_U8,
                              1,
                              int(sample_rate),
                              app_name='midicw',
                              stream_name='TX',
                              device_name='tx0'),
         ]

    paddles = { 1: False, 2: False }

    upload_samples(default_wpm)

    try:
        loop(midiport, pa, paddles)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

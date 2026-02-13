#!/usr/bin/python3

# CW keyer with MIDI input, pyaudio output
#
# Copyright (C) 2022, 2025, 2026 Christoph Berg DF7CB <cb@df7cb.de>
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

import argparse
import mido
import time
import pyaudio
import pulsectl
from itertools import chain
import math
import os

argparser = argparse.ArgumentParser(description="CW keyer with MIDI input, pyaudio output")
argparser.add_argument("-m", "--midiport", default="MidiStomp MIDI 1", help="CW keyer MIDI device")
argparser.add_argument("-c", "--controlport", action=argparse.BooleanOptionalAction, help="Use an Auxiliary MIDI device for speed control")
argparser.add_argument("-n", "--controlport-name", default="DJControl Compact", help="Device name to use as Auxiliary MIDI")
argparser.add_argument("-w", "--wpm", type=int, default=24, help="CW speed in words per minute (PARIS, default 24)")
argparser.add_argument("-p", "--pitch", type=int, default=850, help="CW pitch in Hz (default 850)")
argparser.add_argument("-s", "--txserial", help="serial device to key RTS line on (default none)")
argparser.add_argument("-t", "--txaudio", help="2nd audio output device (e.g. 'tx0, default none')")
args = argparser.parse_args()

# constants
sample_rate = 48000.0
ramp = 0.012 # at least 6ms ramp up/down (CWops recommendation)
volume = 100
word_spacing = 7 # after this many dot_durations of silence a new word begins

# global variables
dah_sample = None
dit_sample = None
dot_duration = None
audiobuffer = []

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
    "-...-.-": '<BK>',
    "........": '<HH>',
}

def erase_chars(chars):
    print('\010' * chars + ' ' * chars + '\010' * chars, end='')

def generate_sample(duration):
    """Generate a sine wave sample of duration+ramp (in seconds)"""

    ramp_samples = int(ramp * sample_rate)
    num_samples = int((duration-ramp) * sample_rate)

    audio = []
    for x in range(ramp_samples):
        audio.append(128+int(volume
                * 0.5 * (1 - math.cos(math.pi * x / ramp_samples)) # cosine ramp up
                * math.sin(2 * math.pi * args.pitch * ( x / sample_rate ))))

    for x in range(ramp_samples, ramp_samples+num_samples):
        audio.append(128+int(volume * math.sin(2 * math.pi * args.pitch * ( x / sample_rate ))))

    for x in range(ramp_samples):
        audio.append(128+int(volume
                * 0.5 * (1 + math.cos(math.pi * x / ramp_samples)) # cosine ramp down
                * math.sin(2 * math.pi * args.pitch * ((ramp_samples+num_samples+x) / sample_rate))))

    return audio

def generate_samples(speed):
    global dot_duration, dit_sample, dah_sample
    dot_duration = 1.2 / speed # 1200ms/speed

    dit_sample = generate_sample(dot_duration)
    dah_sample = generate_sample(3*dot_duration)

def play_samples(audiobuffer, sample):
    for buffer in audiobuffer:
        buffer += sample

def audio_callback(buffer, in_data, frame_count, time_info, status_flags):
    samples = buffer[:frame_count]
    buffer[:] = buffer[frame_count:]
    if len(samples) < frame_count:
        samples += [128 for x in range(frame_count - len(samples))]
    return bytes(samples), pyaudio.paContinue

def audio_callback0(in_data, frame_count, time_info, status_flags):
    return audio_callback(audiobuffer[0], in_data, frame_count, time_info, status_flags)

def audio_callback1(in_data, frame_count, time_info, status_flags):
    return audio_callback(audiobuffer[1], in_data, frame_count, time_info, status_flags)

def poll(midiport, controlport, paddles, blocking=False):
    dit, dah = paddles[1], paddles[2]

    if blocking:
        msgs = chain([midiport.receive()], midiport.iter_pending())
    else:
        msgs = midiport.iter_pending()

    wpm2 = None
    for msg in msgs:
        #print(msg)
        if msg.type == 'note_on':
            if msg.note == 1:
                dit = True
            elif msg.note == 2:
                dah = True
        if msg.type in ('note_on', 'note_off') and msg.note in (1, 2):
            paddles[msg.note] = msg.type == 'note_on'

        continue
        if msg.type == 'control_change' and msg.control == 3:
            wpm2 = msg.value

    if controlport:
        for msg in controlport.iter_pending():
            if msg.type == 'control_change' and msg.control == 0x3D: # VOLUME_B
                wpm2 = round(6.0 + 42.0 * (msg.value / 127.0))

    if wpm2 and wpm2 != args.wpm:
        args.wpm = wpm2
        print(f"<{args.wpm}>", end='', flush=True)
        generate_samples(args.wpm)

    # return True if paddle was pressed or held during this polling period
    return dit, dah

def loop(midiport, controlport, audiobuffer, paddles, txserial):
    state = 'idle'
    sign = '' # character keyed
    sign_len = 0 # size of partial character printed so far

    while True:

        # play sample (asynchronously) for state
        if state == 'dit':
            print('.', end='', flush=True)
            sign += '.'
            sign_len += 1

            now = time.time()
            if txserial: txserial.rts = 1
            play_samples(audiobuffer, dit_sample)
            time.sleep(time.time() - now + dot_duration)
            if txserial: txserial.rts = 0
            time.sleep(dot_duration)

        elif state == 'dah':
            print('-', end='', flush=True)
            sign += '-'
            sign_len += 1

            now = time.time()
            if txserial: txserial.rts = 1
            play_samples(audiobuffer, dah_sample)
            time.sleep(time.time() - now + 3 * dot_duration)
            if txserial: txserial.rts = 0
            time.sleep(dot_duration)

        # read paddle input
        dit, dah = poll(midiport, controlport, paddles, False)

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
                dit, dah = poll(midiport, controlport, paddles, True)
                delay = time.time() - ts

                # if the delay was short enough, the last character was continued
                if delay <= dot_duration and (dit or dah):
                    # last character is continued
                    erase_chars(sign_len)
                    print(sign, end='', flush=True)
                    sign_len = len(sign)
                # otherwise, start a new character or a new word
                else:
                    if delay >= word_spacing * dot_duration:
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
    midiport = mido.open_input(args.midiport)
    midiport.iter_pending() # drain pending notes

    controlport = None
    if args.controlport:
        controlport = mido.open_input(args.controlport_name)

    with pulsectl.Pulse("midicwkeyer-control") as pulse:

        # side tone channel (default device)
        # allocate audiobuffer for this stream
        audiobuffer.append([])
        sink_inputs = {x.index for x in pulse.sink_input_list()}
        # open device with pyaudio
        pyaudio.PyAudio().open(format=pyaudio.paInt8, channels=1, rate=int(sample_rate), output=True, stream_callback=audio_callback0),
        # find my sink_input index using pulsectl
        my_sink_input = {x.index for x in pulse.sink_input_list()} - sink_inputs
        my_sink_input = my_sink_input.pop() # get (hopefully only) element from set
        # move to default audio device
        pulse.sink_input_move(my_sink_input, pulse.sink_default_get().index)

        if args.txaudio:
            # TX tone channel (tx0)
            audiobuffer.append([])
            sink_inputs = {x.index for x in pulse.sink_input_list()}
            pyaudio.PyAudio().open(format=pyaudio.paInt8, channels=1, rate=int(sample_rate), output=True, stream_callback=audio_callback1),
            tx_sink_input = {x.index for x in pulse.sink_input_list()} - sink_inputs
            tx_sink_input = tx_sink_input.pop()
            sinks = {x.name: x.index for x in pulse.sink_list()}
            # move to TX audio device
            pulse.sink_input_move(tx_sink_input, sinks[args.txaudio])

    paddles = { 1: False, 2: False }

    generate_samples(args.wpm)

    txserial = None
    if args.txserial:
        import serial
        txserial = serial.Serial()
        txserial.port = args.serial
        txserial.rts = 0
        txserial.open()

    try:
        loop(midiport, controlport, audiobuffer, paddles, txserial)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

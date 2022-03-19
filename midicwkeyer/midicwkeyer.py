#!/usr/bin/python3

# CW keyer with MIDI input, PulseAudio output
#
# Copyright (C) 2022 Christoph Berg DF7CB <cb@df7cb.de>
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
import pulsectl
from itertools import chain

import math
import os
import struct
import wave

sample_rate = 8000.0
ramp = 10 # 10ms ramp up/down
freq = 850.0
volume = 0.8

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

def upload_sample(pulse, duration, sample_name):
    """Upload a beep of 'duration' milliseconds to PulseAudio as 'sample_name'"""

    ramp_samples = int(ramp * (sample_rate / 1000.0))
    num_samples = int((duration+ramp) * (sample_rate / 1000.0))

    audio = []
    for x in range(ramp_samples):
        audio.append(volume
                * 0.5 * (1 - math.cos(math.pi * x / ramp_samples))
                * math.sin(2 * math.pi * freq * ( x / sample_rate )))

    for x in range(ramp_samples, num_samples):
        audio.append(volume * math.sin(2 * math.pi * freq * ( x / sample_rate )))

    for x in range(ramp_samples):
        audio.append(volume
                * 0.5 * (1 - math.cos(math.pi * (ramp_samples-x) / ramp_samples))
                * math.sin(2 * math.pi * freq * ((x+num_samples) / sample_rate)))

    wav_file_name = f"/tmp/{sample_name}.wav"
    wav_file = wave.open(wav_file_name, 'w')

    # wav params
    nchannels = 1
    sampwidth = 2
    nframes = len(audio)
    comptype = "NONE"
    compname = "not compressed"
    wav_file.setparams((nchannels, sampwidth, sample_rate, nframes, comptype, compname))

    for sample in audio:
        wav_file.writeframes(struct.pack('h', int(sample * 32767.0)))

    wav_file.close()

    os.system(f"pactl upload-sample {wav_file_name} {sample_name}")

def upload_samples(pulse, paddles, speed):
    dot_duration = int(1200 / speed)
    dah_duration = 3 * dot_duration

    if dot_duration not in paddles['sample_durations']:
        upload_sample(pulse, dot_duration, f"cw{dot_duration:03}")
        paddles['sample_durations'].add(dot_duration)
    paddles['dit_sample'] = f"cw{dot_duration:03}"
    paddles['dot_duration'] = dot_duration / 1000

    if dah_duration not in paddles['sample_durations']:
        upload_sample(pulse, dah_duration, f"cw{dah_duration:03}")
        paddles['sample_durations'].add(dah_duration)
    paddles['dah_sample'] = f"cw{dah_duration:03}"

def poll(midiport, pulse, paddles, blocking=False):
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
            upload_samples(pulse, paddles, msg.value)

    # return True if paddle was pressed or held during this polling period
    return dit, dah

def loop(midiport, pulse, paddles):
    state = 'idle'
    sign = '' # character keyed
    sign_len = 0 # size of partial character printed so far

    while True:

        # play sample (asynchronously) for state
        if state == 'dit':
            print('.', end='', flush=True)
            sign += '.'
            sign_len += 1
            pulse.play_sample(paddles['dit_sample'], paddles['sidetoneport'])
            pulse.play_sample(paddles['dit_sample'], paddles['txport'])
        elif state == 'dah':
            print('-', end='', flush=True)
            sign += '-'
            sign_len += 1
            pulse.play_sample(paddles['dah_sample'], paddles['sidetoneport'])
            pulse.play_sample(paddles['dah_sample'], paddles['txport'])

        # sleep for state
        if state == 'idle':
            pass
        elif state == 'dah':
            time.sleep(3 * paddles['dot_duration'])
        else:
            time.sleep(paddles['dot_duration'])

        # read paddle input
        dit, dah = poll(midiport, pulse, paddles, False)

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
                dit, dah = poll(midiport, pulse, paddles, True)
                delay = time.time() - ts

                # if the delay was short enough, the last character was continued
                if delay <= paddles['dot_duration'] and (dit or dah):
                    # last character is continued
                    erase_chars(sign_len)
                    print(sign, end='', flush=True)
                    sign_len = len(sign)
                # otherwise, start a new character or a new word
                else:
                    if delay >= 5 * paddles['dot_duration']:
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
    pulse = pulsectl.Pulse('cw-sidetone')

    paddles = {
            1: False,
            2: False,
            'dit_du': None,
            'dah_sample': None,
            'dit_sample': None,
            'dot_duration': None,
            'sample_durations': set(),
            'txport': pulse.server_info().default_sink_name,
            'sidetoneport': pulse.server_info().default_sink_name,
    }

    upload_samples(pulse, paddles, 24)

    for sink in pulse.sink_list():
        if sink.description.startswith('tx0'):
            paddles['txport'] = sink.index
            print(f"TX port is {sink.description} ({sink.index})")
        elif sink.description.startswith('Plantronics'):
            paddles['sidetoneport'] = sink.index
            print(f"Sidetone port is {sink.description} ({sink.index})")

    try:
        loop(midiport, pulse, paddles)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

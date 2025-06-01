import numpy as np
from gnuradio import gr
import pmt

import os
import pulsectl

# buttons (notes)
MIDI_FT8_QRG = 2 # KP 2 A
MIDI_SHIFT_FT8_QRG = 6 # Shift-KP 2 A
MIDI_SYNC_A = 35
MIDI_SHIFT_SYNC_A = 38
MIDI_RECORD = 43

MIDI_AUDIO_HEADPHONES = 49 # KP 1 B
MIDI_AUDIO_SPEAKER = 51 # KP 3 B
MIDI_AUDIO_STEREO = 52 # KP 4 B
MIDI_AUDIOS = [MIDI_AUDIO_HEADPHONES, MIDI_AUDIO_STEREO, MIDI_AUDIO_SPEAKER]

# controls
MIDI_VFO_A = 48 # Jog A
MIDI_SHIFT_VFO_A = 55 # Shift-Jog A
MIDI_POWER = 54 # Sync A
MIDI_VOLUME = 57 # Volume A
MIDI_BANDPASS_CENTER = 59 # Medium A
MIDI_BANDPASS_WIDTH = 60 # Bass A
MIDI_WPM = 0x3D
MIDI_REPORT_ALL_CONTROLS = 0x7f

def sign(i):
    if i < 0:
        return -1
    elif i > 0:
        return 1
    else:
        return 0

class blk(gr.sync_block):
    """TRX Control block"""

    def __init__(self):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Control',
            in_sig=None,
            out_sig=None,
        )

        self.message_port_register_in(pmt.intern("midi_in"))
        self.set_msg_handler(pmt.intern("midi_in"), self.midi_in)
        self.message_port_register_in(pmt.intern("rx_freq_in"))
        self.set_msg_handler(pmt.intern("rx_freq_in"), self.rx_freq_in)
        self.message_port_register_in(pmt.intern("tx_freq_in"))
        self.set_msg_handler(pmt.intern("tx_freq_in"), self.tx_freq_in)

        self.message_port_register_out(pmt.intern("midi_out"))
        self.message_port_register_out(pmt.intern("rx_freq_out"))
        self.message_port_register_out(pmt.intern("tx_freq_out"))
        self.message_port_register_out(pmt.intern("wpm_out"))
        self.message_port_register_out(pmt.intern("filter_center_out"))
        self.message_port_register_out(pmt.intern("filter_bw_out"))
        self.message_port_register_out(pmt.intern("af_gain_out"))

        self.rx0_freq = 40000.0
        self.tx_freq = 40000.0
        self.filter_center = 850
        self.filter_bw = 3000
        self.record = False
        self.sync_a = False # start false so set_sync_a sets the LEDs
        self.vfo_a_dir = 0 # last tuning direction

        self.pulse = None
        self.tx_audio_port = None
        self.rx_audio_port = None
        self.ft8_audio_port = None

    def note_on(self, note, velocity):
        self.message_port_pub(pmt.intern("midi_out"),
                pmt.cons(pmt.intern('note_on'),
                    pmt.cons(pmt.from_long(note), pmt.from_long(velocity))))

    def start(self):

        # Audio
        self.pulse = pulsectl.Pulse('qo100')

        for port in self.pulse.source_output_list():
            # device.description: ALSA Capture [python3.13]
            desc = port.proplist.get('device.description')
            if desc and desc.startswith("ALSA Capture [python"):
                self.tx_audio_port = port
                print("TX port:", self.tx_audio_port)
                self.set_audio_input('tx0')
                break

        for port in self.pulse.sink_input_list():
            # device.description: ALSA Playback [python3.13]
            desc = port.proplist.get('device.description')
            if desc and desc.startswith("ALSA Playback [python"):
                if "remote.name" in port.proplist: # "pipewire-0" on the FT8 sink
                    self.ft8_audio_port = port
                    print("FT8 port:", self.ft8_audio_port)
                    # need to restore volume since pipewire can't tell the ports apart and randomly remembers the last setting from either
                    self.ft8_audio_port.volume.value_flat = 1.0
                    self.pulse.sink_input_volume_set(self.ft8_audio_port.index, self.ft8_audio_port.volume)
                    # connect to rx2
                    rx2_sink = self.pulse.get_sink_by_name("rx2")
                    self.pulse.sink_input_move(self.ft8_audio_port.index, rx2_sink.index)
                elif self.rx_audio_port is None:
                    self.rx_audio_port = port
                    print("RX port:", self.rx_audio_port)
                    # volume will be set by polling the current console settings
                    # connect to sink
                    self.set_audio_output(MIDI_AUDIO_SPEAKER, 'Internes Audio')

        # MIDI
        self.set_sync_a(True)
        self.set_rx_freq(40000.0)
        self.set_tx_freq(40000.0)
        self.set_record(False)

        # read out knobs and slider on startup
        self.message_port_pub(pmt.intern("midi_out"),
                pmt.cons(pmt.intern('control_change'),
                    pmt.cons(pmt.from_long(MIDI_REPORT_ALL_CONTROLS), pmt.from_long(127))))

        # without this, the spectrum display updates only once per second (GR bug?)
        #self.tb.vfo0_spectrum.set_fft_size(2048)

        # create temp directory
        try: os.mkdir("/run/user/1000/gnuradio")
        except: pass

    def set_audio_volume(self, new_volume):
        try:
            #rx_sink = self.pulse.sink_default_get()
            #rx_sink.volume.value_flat = new_volume
            #self.pulse.sink_volume_set(rx_sink.index, rx_sink.volume)
            self.rx_audio_port.volume.value_flat = new_volume
            self.pulse.sink_input_volume_set(self.rx_audio_port.index, self.rx_audio_port.volume)
            self.message_port_pub(pmt.intern("af_gain_out"),
                pmt.cons(pmt.intern('value'), pmt.from_double(new_volume)))

        except Exception as e:
            print("Error setting volume:", e)

    def set_audio_output(self, midi_key, sink_name):
        try:
            for sink in self.pulse.sink_list():
                if sink_name in sink.description:
                    self.pulse.sink_input_move(self.rx_audio_port.index, sink.index)
                    break

            for key in MIDI_AUDIOS:
                self.note_on(key, 127 if key == midi_key else 0)

        except Exception as e:
            print(f"Error setting audio output to {sink_name}:", e)

    def set_audio_input(self, source_name):
        try:
            for source in self.pulse.source_list():
                if source.description.startswith(source_name):
                    self.pulse.source_output_move(self.tx_audio_port.index, source.index)
                    break

        except Exception as e:
            print(f"Error setting audio input to {source_name}:", e)

    def set_record(self, record):
        self.record = record
        self.note_on(MIDI_RECORD, 127 if self.record else 0)
        if self.record:
            self.set_audio_input(self.pulse.source_default_get().description)
        else:
            self.set_audio_input('Monitor of tx0')

    def set_rx_freq(self, freq):
        self.message_port_pub(pmt.intern("rx_freq_out"),
                pmt.cons(pmt.intern('freq'), pmt.from_double(freq)));

    def set_tx_freq(self, freq):
        self.message_port_pub(pmt.intern("tx_freq_out"),
                pmt.cons(pmt.intern('freq'), pmt.from_double(freq)));

    def set_wpm(self, wpm):
        self.message_port_pub(pmt.intern("wpm_out"),
                pmt.cons(pmt.intern('value'), pmt.from_double(wpm)));

    def set_sync_a(self, sync_a):
        if self.sync_a != sync_a:
            self.sync_a = sync_a
            self.note_on(MIDI_SYNC_A, 127 if sync_a else 0)
            self.note_on(MIDI_SHIFT_SYNC_A, 127 if sync_a else 0)
            if sync_a:
                self.set_tx_freq(self.rx0_freq)

    def rx_freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            self.rx0_freq = int(pmt.to_double(pmt.cdr(msg)))
            if self.sync_a:
                self.set_tx_freq(self.rx0_freq)

    def tx_freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            tx_freq = int(pmt.to_double(pmt.cdr(msg)))

            if (tx_freq == 40000) != (self.tx_freq == 40000):
                # FT8 frequency indicator LED
                self.note_on(MIDI_FT8_QRG, 127 if tx_freq == 40000 else 0)
                self.note_on(MIDI_SHIFT_FT8_QRG, 127 if tx_freq == 40000 else 0)

            self.tx_freq = tx_freq

            if self.tx_freq != self.rx0_freq:
                self.set_sync_a(False)

            freqfile = open("/run/user/1000/gnuradio/qo100.qrg", "w")
            freqfile.write(str(tx_freq + 2400000000) + "\n")
            # fake frequency on 10m so tlf can deal with it
            #freqfile.write(str(tx_freq + 28000000) + "\n")
            freqfile.close()

    def midi_in(self, msg):
        if not msg.is_pair(): return
        msgtype = str(pmt.car(msg))

        if msgtype == 'control_change':
            payload = pmt.cdr(msg)
            control = pmt.to_long(pmt.car(payload))
            value = pmt.to_long(pmt.cdr(payload))

            if control == MIDI_VFO_A: # jog A
                delta = value if value < 64 else value - 128
                if sign(delta) != self.vfo_a_dir: # compensate for 2 (or 126) output on direction change
                    delta += self.vfo_a_dir
                    self.vfo_a_dir = sign(delta)
                self.set_rx_freq(self.rx0_freq + delta * 10)

            elif control == MIDI_SHIFT_VFO_A and value != 64: # shift-jog a (64 reported on all-buttons-readout, ignore that)
                delta = value if value < 64 else value - 128
                if sign(delta) != self.vfo_a_dir: # compensate for 2 (or 126) output on direction change
                    delta += self.vfo_a_dir
                    self.vfo_a_dir = sign(delta)
                self.set_sync_a(False)
                self.set_tx_freq(self.tx_freq + delta * 10)

            elif control == MIDI_VOLUME:
                self.set_audio_volume(value / 100.0) # 0 .. 127%

            elif control == MIDI_WPM:
                wpm = round(6.0 + 42.0 * value / 127.0) # 0 .. 127% -> 6..48 wpm
                self.set_wpm(wpm)

            elif control in (MIDI_BANDPASS_CENTER, MIDI_BANDPASS_WIDTH): # medium A, bass A
                if control == MIDI_BANDPASS_CENTER:
                    self.filter_center = 1500 + 20 * (value - 64)
                    self.message_port_pub(pmt.intern("filter_center_out"),
                        pmt.cons(pmt.intern('value'), pmt.from_double(self.filter_center)))
                if control == MIDI_BANDPASS_WIDTH:
                    if value < 127 - 36: # first 36 steps are 30Hz, the rest 20Hz
                        self.filter_bw = 3000 - 360 - 20 * (127 - value)
                    else:
                        self.filter_bw = 3000 - 30 * (127 - value)
                    self.message_port_pub(pmt.intern("filter_bw_out"),
                        pmt.cons(pmt.intern('value'), pmt.from_double(self.filter_bw)))

                low_cutoff = max(self.filter_center - self.filter_bw // 2, 0)
                high_cutoff = min(self.filter_center + self.filter_bw // 2, 3000)
                self.tb.set_rx0_low_cutoff(low_cutoff)
                self.tb.set_rx0_high_cutoff(high_cutoff)

            elif control == MIDI_POWER:
                power = 0.1 + 0.9 * (value/127.0)
                self.tb.set_tx_power(power)

            else:
                print("Unknown MIDI control_change:", control, value)

        elif msgtype == 'note_on':
            payload = pmt.cdr(msg)
            note = pmt.to_long(pmt.car(payload))
            velocity = pmt.to_long(pmt.cdr(payload))

            if velocity != 127: # ignore key releases
                return

            if note == MIDI_SYNC_A: # Sync A
                self.set_sync_a(not self.sync_a)

            elif note == MIDI_SHIFT_SYNC_A: # Shift-Sync A
                if not self.sync_a:
                    # set RX from TX
                    self.set_rx_freq(self.tx_freq)
                self.set_sync_a(not self.sync_a)

            elif note == MIDI_FT8_QRG: # KP 2 A
                self.set_rx_freq(40000)
                self.set_sync_a(True)
                self.set_record(False)

            elif note == MIDI_AUDIO_HEADPHONES: # KP 1 A
                self.set_audio_output(MIDI_AUDIO_HEADPHONES, 'Plantronics')

            elif note == MIDI_AUDIO_STEREO: # KP 3 A
                self.set_audio_output(MIDI_AUDIO_STEREO, 'Internes Audio Analog Stereo')

            elif note == MIDI_AUDIO_SPEAKER: # KP 4 A
                self.set_audio_output(MIDI_AUDIO_SPEAKER, 'Unitek Y')

            elif note == MIDI_RECORD: # REC
                self.set_record(not self.record)

            else:
                print("Unknown MIDI note_on:", note, velocity)

        else:
            print("Unknown MIDI message type:", msgtype)

if __name__ == '__main__':
    blk()

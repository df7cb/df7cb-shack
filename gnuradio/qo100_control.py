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
MIDI_REPORT_ALL_CONTROLS = 0x7f

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

        self.rx0_freq = 40000.0
        self.tx_freq = 40000.0
        self.filter_center = 850
        self.filter_bw = 3000
        self.record = False
        self.sync_a = False # start false so set_sync_a sets the LEDs

        self.pulse = None

    def note_on(self, note, velocity):
        self.message_port_pub(pmt.intern("midi_out"),
                pmt.cons(pmt.intern('note_on'),
                    pmt.cons(pmt.from_long(note), pmt.from_long(velocity))))

    def start(self):
        self.pulse = pulsectl.Pulse('qo100')

        # MIDI
        self.set_sync_a(True)
        self.set_rx_freq(40000.0)
        self.set_tx_freq(40000.0)
        self.set_record(False)

        # Audio output
        self.set_audio_output(MIDI_AUDIO_SPEAKER, 'Unitek Y')

        # read out knobs and slider on startup
        self.message_port_pub(pmt.intern("midi_out"),
                pmt.cons(pmt.intern('control_change'),
                    pmt.cons(pmt.from_long(MIDI_REPORT_ALL_CONTROLS), pmt.from_long(127))))

        # without this, the spectrum display updates only once per second (GR bug?)
        self.tb.vfo0_spectrum.set_fft_size(2048)

        # create temp directory
        try: os.mkdir("/run/user/1000/gnuradio")
        except: pass

    def set_audio_volume(self, new_volume):
        try:
            rx2_sink_index = [x.index for x in self.pulse.sink_list() if x.description == 'rx2'][0]
            # the rx0 sink is the one not connected to rx2
            rx0_sink = [self.pulse.sink_info(x.sink) for x in self.pulse.sink_input_list() if int(x.proplist.get('application.process.id')) == os.getpid() and x.sink != rx2_sink_index][0]
            rx0_sink.volume.value_flat = new_volume
            self.pulse.sink_volume_set(rx0_sink.index, rx0_sink.volume)
        except Exception as e:
            print(e)

    def set_audio_output(self, midi_key, sink_name):
        try:
            rx2_sink_index = [x.index for x in self.pulse.sink_list() if x.description == 'rx2'][0]
            # the rx0 sink is the one not connected to rx2
            rx0_audio = [x.index for x in self.pulse.sink_input_list() if int(x.proplist.get('application.process.id')) == os.getpid() and x.sink != rx2_sink_index][0]

            for sink in self.pulse.sink_list():
                if sink_name in sink.description:
                    self.pulse.sink_input_move(rx0_audio, sink.index)
                    break

            for key in MIDI_AUDIOS:
                self.note_on(key, 127 if key == midi_key else 0)

        except Exception as e:
            print(e)

    def set_audio_input(self, source_name):
        try:
            tx_audio = [x.index for x in self.pulse.source_output_list() if int(x.proplist.get('application.process.id')) == os.getpid()][0]

            for source in self.pulse.source_list():
                if source.description.startswith(source_name):
                    self.pulse.source_output_move(tx_audio, source.index)
                    break
        except Exception as e:
            print(e)

    def set_record(self, record):
        self.record = record
        self.note_on(MIDI_RECORD, 127 if self.record else 0)
        if self.record:
            self.set_audio_input('Plantronics')
        else:
            self.set_audio_input('Monitor of tx0')

    def set_rx_freq(self, freq):
        self.message_port_pub(pmt.intern("rx_freq_out"),
                pmt.cons(pmt.intern('freq'), pmt.from_double(freq)));

    def set_tx_freq(self, freq):
        self.message_port_pub(pmt.intern("tx_freq_out"),
                pmt.cons(pmt.intern('freq'), pmt.from_double(freq)));

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
                self.set_rx_freq(self.rx0_freq + delta * 20)

            elif control == MIDI_SHIFT_VFO_A and value != 64: # shift-jog a (64 reported on all-buttons-readout, ignore that)
                delta = value if value < 64 else value - 128
                self.set_sync_a(False)
                self.set_tx_freq(self.tx_freq + delta * 20)

            elif control == MIDI_VOLUME:
                self.set_audio_volume(value / 100.0) # 0 .. 127%

            elif control in (MIDI_BANDPASS_CENTER, MIDI_BANDPASS_WIDTH): # medium A, bass A
                if control == MIDI_BANDPASS_CENTER:
                    self.filter_center = 100 + int(2800 * (value / 127.0))
                if control == MIDI_BANDPASS_WIDTH:
                    self.filter_bw = 100 + int(2900 * (value / 127.0))

                low_cutoff = max(self.filter_center - self.filter_bw // 2, 0)
                high_cutoff = min(self.filter_center + self.filter_bw // 2, 3000)
                self.tb.set_rx0_low_cutoff(low_cutoff)
                self.tb.set_rx0_high_cutoff(high_cutoff)

            if control == MIDI_POWER:
                power = 0.1 + 0.9 * (value/127.0)
                self.tb.set_tx_power(power)

        elif msgtype == 'note_on':
            payload = pmt.cdr(msg)
            note = pmt.to_long(pmt.car(payload))
            velocity = pmt.to_long(pmt.cdr(payload))

            if note == MIDI_SYNC_A and velocity == 127: # Sync A
                self.set_sync_a(not self.sync_a)

            elif note == MIDI_SHIFT_SYNC_A and velocity == 127: # Shift-Sync A
                if not self.sync_a:
                    # set RX from TX
                    self.set_rx_freq(self.tx_freq)
                self.set_sync_a(not self.sync_a)

            elif note == MIDI_FT8_QRG and velocity == 127: # KP 2 A
                self.set_rx_freq(40000)
                self.set_sync_a(True)
                self.set_record(False)

            elif note == MIDI_AUDIO_HEADPHONES and velocity == 127: # KP 1 A
                self.set_audio_output(MIDI_AUDIO_HEADPHONES, 'Plantronics')

            elif note == MIDI_AUDIO_STEREO and velocity == 127: # KP 3 A
                self.set_audio_output(MIDI_AUDIO_STEREO, 'Internes Audio Analog Stereo')

            elif note == MIDI_AUDIO_SPEAKER and velocity == 127: # KP 4 A
                self.set_audio_output(MIDI_AUDIO_SPEAKER, 'Unitek Y')

            if note == MIDI_RECORD and velocity == 127: # REC
                self.set_record(not self.record)

if __name__ == '__main__':
    blk()

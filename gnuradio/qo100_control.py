import numpy as np
from gnuradio import gr
import pmt

MIDI_POWER = 54

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

        self.filter_center = 850
        self.filter_bw = 3000

        self.sync_a = True
        #self.record = True

    def note_on(self, note, velocity):
        self.message_port_pub(pmt.intern("midi_out"),
                pmt.cons(pmt.intern('note_on'),
                    pmt.cons(pmt.from_long(note), pmt.from_long(velocity))))

    def start(self):
        # MIDI
        self.note_on(35, 127) # Sync A
        #self.note_on(43, 127) # REC
        self.tb.set_vfo(40000.0)
        self.tb.set_tx_vfo(40000.0)

        # without this, the spectrum display updates only once per second (GR bug?)
        self.tb.vfo0_spectrum.set_fft_size(2048)

    def set_rx_freq(self, freq):
        self.tb._vfo_msgdigctl_win.setValue(freq)
        self.tb.set_vfo(freq)
        if self.sync_a:
            self.set_tx_freq(freq)

    def set_tx_freq(self, freq):
        self.tb._tx_vfo_msgdigctl_win.setValue(freq)
        self.tb.set_tx_vfo(freq)

    def rx_freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            if self.sync_a:
                freq = int(pmt.to_double(pmt.cdr(msg)))
                self.set_tx_freq(freq)

    def tx_freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            tx_freq = int(pmt.to_double(pmt.cdr(msg)))

            # FT8 indicator LED
            self.note_on(2, 127 if tx_freq == 40000 else 0)
            self.note_on(6, 127 if tx_freq == 40000 else 0) # shift-KP 2 A

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

            if control == 48: # jog A
                delta = value if value < 64 else value - 128
                self.set_rx_freq(self.tb.get_vfo() + delta * 20)

            elif control == 55: # shift-jog a
                delta = value if value < 64 else value - 128
                if self.sync_a:
                    self.sync_a = False
                    self.note_on(35, 0)
                self.set_tx_freq(self.tb.get_tx_vfo() + delta * 20)

            elif control in (59, 60): # medium A, bass A
                if control == 59:
                    self.filter_center = 100 + int(2800 * (value / 127.0))
                if control == 60:
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

            if note == 35 and velocity == 127: # Sync A
                self.sync_a = not self.sync_a
                self.note_on(35, 127 if self.sync_a else 0)
                if self.sync_a:
                    self.set_tx_freq(self.tb.get_vfo())

            if note == 2 and velocity == 127: # KP 2 A
                self.sync_a = True
                self.note_on(35, 127)
                self.set_rx_freq(40000)

            #if note == 43 and velocity == 127: # REC
            #    self.record = not self.record
            #    self.note_on(43, 127 if self.record else 0)
            #    if self.record:
            #        self.tb.rx_waterfall.start()
            #    else:
            #        self.tb.rx_waterfall.stop()

if __name__ == '__main__':
    blk()

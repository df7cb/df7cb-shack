import numpy as np
from gnuradio import gr
import pmt

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

        self.message_port_register_out(pmt.intern("rx_freq_out"))
        self.message_port_register_out(pmt.intern("tx_freq_out"))
        self.message_port_register_out(pmt.intern("rx0_low_cutoff"))
        self.message_port_register_out(pmt.intern("rx0_high_cutoff"))
        self.message_port_register_out(pmt.intern("midi_out"))

        self.rx_freq = 40000
        self.tx_freq = 40000
        self.filter_center = 850
        self.filter_bw = 3000

        self.sync_a = True

    def note_on(self, note, velocity):
        self.message_port_pub(pmt.intern("midi_out"),
                pmt.cons(pmt.intern('note_on'),
                    pmt.cons(pmt.from_long(note), pmt.from_long(velocity))))

    def start(self):
        self.note_on(35, 127) # Sync A
        self.set_rx_freq(self.rx_freq)

    def set_rx_freq(self, freq):
        self.rx_freq = min(max(freq, -10000), 510000)
        self.message_port_pub(pmt.intern("rx_freq_out"), pmt.cons(pmt.intern('freq'), pmt.from_long(freq)))
        if self.sync_a:
            self.set_tx_freq(self.rx_freq)

    def set_tx_freq(self, freq):
        self.tx_freq = min(max(freq, -10000), 510000)
        self.message_port_pub(pmt.intern("tx_freq_out"), pmt.cons(pmt.intern('freq'), pmt.from_long(freq)))
        # FT8 indicator LED
        self.note_on(2, 127 if freq == 40000 else 0)
        self.note_on(6, 127 if freq == 40000 else 0) # shift-KP 2 A

    def rx_freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            self.rx_freq = int(pmt.to_double(pmt.cdr(msg)))
            #if self.sync_a:
            #    self.set_tx_freq(self.rx_freq)

    def tx_freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            self.tx_freq = int(pmt.to_double(pmt.cdr(msg)))

    def midi_in(self, msg):
        if not msg.is_pair(): return
        msgtype = str(pmt.car(msg))

        if msgtype == 'control_change':
            payload = pmt.cdr(msg)
            control = pmt.to_long(pmt.car(payload))
            value = pmt.to_long(pmt.cdr(payload))

            if control == 48: # jog A
                delta = value if value < 64 else value - 128
                self.set_rx_freq(self.rx_freq + delta * 20)

            elif control == 55: # shift-jog a
                delta = value if value < 64 else value - 128
                if self.sync_a:
                    self.sync_a = False
                    self.note_on(35, 0)
                self.set_tx_freq(self.tx_freq + delta * 20)

            elif control in (59, 60): # medium A, bass A
                if control == 59:
                    self.filter_center = 100 + int(2800 * (value / 127.0))
                if control == 60:
                    self.filter_bw = 100 + int(2900 * (value / 127.0))

                low_cutoff = max(self.filter_center - self.filter_bw // 2, 0)
                high_cutoff = min(self.filter_center + self.filter_bw // 2, 3000)

                self.message_port_pub(pmt.intern("rx0_low_cutoff"), pmt.cons(pmt.intern('value'), pmt.from_long(low_cutoff)))
                self.message_port_pub(pmt.intern("rx0_high_cutoff"), pmt.cons(pmt.intern('value'), pmt.from_long(high_cutoff)))

        elif msgtype == 'note_on':
            payload = pmt.cdr(msg)
            note = pmt.to_long(pmt.car(payload))
            velocity = pmt.to_long(pmt.cdr(payload))

            if note == 35 and velocity == 127: # Sync A
                self.sync_a = not self.sync_a
                self.note_on(35, 127 if self.sync_a else 0)
                if self.sync_a:
                    self.set_tx_freq(self.rx_freq)

            if note == 2 and velocity == 127: # KP 2 A
                self.sync_a = True
                self.note_on(35, 127)
                self.set_rx_freq(40000)


if __name__ == '__main__':
    blk()

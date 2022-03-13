import numpy as np
from gnuradio import gr
import pmt
import mido
import threading

class blk(gr.sync_block):
    """MIDI Source block"""

    def __init__(self, midi_port='DJControl Compact:DJControl Compact DJControl Com'):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='MIDI Source',
            in_sig=None,
            out_sig=None,
        )
        self.midi_port = midi_port

        self.message_port_register_in(pmt.intern("midi_in"))
        self.set_msg_handler(pmt.intern("midi_in"), self.midi_message)
        self.message_port_register_out(pmt.intern("midi_out"))

    def start(self):
        self.midiport = mido.open_ioport(self.midi_port)

        self.midithread = threading.Thread(target=self.midi, daemon=True)
        self.midithread.start()

    def midi(self):
        for msg in self.midiport:

            if msg.type == 'control_change':
                self.message_port_pub(pmt.intern("midi_out"),
                        pmt.cons(pmt.intern('control_change'),
                            pmt.cons(pmt.from_long(msg.control), pmt.from_long(msg.value))))

            elif msg.type == 'note_on':
                self.message_port_pub(pmt.intern("midi_out"),
                        pmt.cons(pmt.intern('note_on'),
                            pmt.cons(pmt.from_long(msg.note), pmt.from_long(msg.velocity))))
            else:
                self.message_port_pub(pmt.intern("midi_out"), pmt.string_to_symbol(str(msg)))

    def midi_message(self, msg):
        if not msg.is_pair(): return
        msgtype = str(pmt.car(msg))

        if msgtype == 'note_on':
            payload = pmt.cdr(msg)
            note = pmt.to_long(pmt.car(payload))
            velocity = pmt.to_long(pmt.cdr(payload))

            self.midiport.send(mido.Message('note_on', note=note, velocity=velocity))

        elif msgtype == 'control_change':
            payload = pmt.cdr(msg)
            control = pmt.to_long(pmt.car(payload))
            value = pmt.to_long(pmt.cdr(payload))

            self.midiport.send(mido.Message('control_change', control=control, value=value))

if __name__ == '__main__':
    blk()

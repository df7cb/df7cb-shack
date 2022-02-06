"""
CW Modulator Block
"""

import numpy as np
from gnuradio import gr
import pmt

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """CW Modulator block"""

    def __init__(self, transition=1000):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='CW Modulator',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=[np.float32]
        )
        # ramp up signal over this many ticks
        self.transition = transition
        self.level = 0
        self.keyed = False

        self.message_port_register_in(pmt.intern("key"))
        self.set_msg_handler(pmt.intern('key'), self.key)

    def key(self, msg):
        if pmt.is_pair(msg) and pmt.car(msg) == pmt.intern('key'):
            self.keyed = pmt.to_bool(pmt.cdr(msg))

    def work(self, input_items, output_items):
        for i in range(len(output_items[0])):
            if self.keyed and self.level < self.transition:
                self.level += 1
            if not self.keyed and self.level > 0:
                self.level -= 1
            factor = 0.5 * (1 - np.cos(np.pi * self.level / self.transition))
            output_items[0][i] = input_items[0][i] * factor
        return len(output_items[0])

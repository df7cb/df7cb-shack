"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import pmt

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Embedded Python Block',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=[np.float32]
        )
        self.message_port_register_in(pmt.intern("cw_in"))
        self.set_msg_handler(pmt.intern('cw_in'), self.key)
        self.keyed = 0.0

    def key(self, msg):
        if pmt.car(msg) == pmt.intern('cw'):
            self.keyed = pmt.to_float(pmt.cdr(msg))

    def work(self, input_items, output_items):
        output_items[0][:] = input_items[0] * self.keyed
        return len(output_items[0])

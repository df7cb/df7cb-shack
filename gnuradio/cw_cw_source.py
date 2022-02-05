"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import pmt
import threading
import serial

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, port='/dev/ttyUSBK3NG'):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='CW Source',   # will show up in GRC
            in_sig=None,
            out_sig=None,
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.port = port

        #self.message_port_register_in(pmt.intern("freq_in"))
        #self.message_port_register_out(pmt.intern("freq_out"))
        self.message_port_register_out(pmt.intern("cw_out"))
        #self.set_msg_handler(pmt.intern('freq_in'), self.freq_in)

    def start(self):
        self.serial = serial.Serial(self.port, 1200)

        self.cwthread = threading.Thread(target=self.cw, daemon=True)
        self.cwthread.start()

    def cw(self):
        while True:
            try:
                x = self.serial.read()
            except Exception as e:
                self.message_port_pub(pmt.intern("cw_out"),
                        pmt.cons(pmt.intern('cw'), pmt.from_float(0.0)))
                self.message_port_pub(pmt.intern("cw_out"),
                        pmt.cons(pmt.intern('error'), pmt.string_to_symbol(str(e))))
            if x in (b'^', b'_'):
                ampl = 0.5 if x == b'^' else 0.0
                self.message_port_pub(pmt.intern("cw_out"),
                        pmt.cons(pmt.intern('cw'), pmt.from_float(ampl)))

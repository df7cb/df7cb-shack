import numpy as np
from gnuradio import gr
import pmt
import threading
import serial

class blk(gr.sync_block):
    """Read CW input from modified K3NG keyer"""

    def __init__(self, port='/dev/ttyUSBK3NG'):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='CW Source',
            in_sig=None,
            out_sig=None,
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.port = port

        self.message_port_register_out(pmt.intern("key"))

    def start(self):
        self.serial = serial.Serial(self.port, 1200)

        self.cwthread = threading.Thread(target=self.cw, daemon=True)
        self.cwthread.start()

    def set_key(self, key):
        self.message_port_pub(pmt.intern("key"),
                pmt.cons(pmt.intern("key"), pmt.from_bool(key)))

    def cw(self):
        while True:
            try:
                x = self.serial.read()
                if x in (b'^', b'_'):
                    self.set_key(x == b'^')
            except Exception as e:
                self.set_key(False) # turn signal off on error
                print(e)

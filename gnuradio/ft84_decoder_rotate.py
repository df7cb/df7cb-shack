from gnuradio import gr
import pmt
import os
import subprocess

class blk(gr.basic_block):
    """Rotate wav files and feed them to jt9 for FT8 and FT4 decoding"""

    def __init__(self):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Rotate and Decode Wav File',   # will show up in GRC
            in_sig=None,
            out_sig=None,
        )

        self.message_port_register_in(pmt.intern("rotate_ft8"))
        self.set_msg_handler(pmt.intern("rotate_ft8"), self.rotate_ft8)
        self.message_port_register_in(pmt.intern("rotate_ft4"))
        self.set_msg_handler(pmt.intern("rotate_ft4"), self.rotate_ft4)

    def rotate_and_decode(self, mode, sink):
        # rotate file
        try: os.unlink(mode + ".wav")
        except: pass
        try: os.rename(mode + "-tmp.wav", mode + ".wav")
        except: pass

        # ask sink to re-open file
        sink.open(mode + "-tmp.wav")

        # decode it
        res = subprocess.run(["jt9", "--" + mode, mode + ".wav"], capture_output=True)
        out = res.stdout.decode()

        for line in out.split("\n"):
            if line[:6] == "000000":
                print(mode, line)

    def rotate_ft8(self, msg):
        self.rotate_and_decode("ft8", self.tb.ft8_sink)

    def rotate_ft4(self, msg):
        self.rotate_and_decode("ft4", self.tb.ft4_sink)

if __name__ == "__main__":
    b = blk()
    b.rotate('foo')

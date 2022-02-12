from gnuradio import gr
import pmt
import os
import subprocess
import time

class blk(gr.basic_block):
    """Rotate wav files and feed them to jt9 for FT8 and FT4 decoding"""

    def __init__(self, tmp_path='.'):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Rotate and Decode Wav File',   # will show up in GRC
            in_sig=None,
            out_sig=None,
        )
        self.tmp_path = tmp_path

        self.message_port_register_in(pmt.intern("rotate_ft8"))
        self.set_msg_handler(pmt.intern("rotate_ft8"), self.rotate_ft8)
        self.message_port_register_in(pmt.intern("rotate_ft4"))
        self.set_msg_handler(pmt.intern("rotate_ft4"), self.rotate_ft4)

    def start(self):
        try: os.mkdir(self.tmp_path)
        except: pass

        self.all_txt = open("ft84.txt", "a")

    def rotate_and_decode(self, mode, sink, interval):
        tmp_file = f"{self.tmp_path}/{mode}-tmp.wav"
        decode_file = f"{self.tmp_path}/{mode}.wav"

        # rotate file
        try: os.unlink(decode_file)
        except: pass
        try: os.rename(tmp_file, decode_file)
        except: pass

        # ask sink to re-open file
        sink.open(tmp_file)

        stamp = time.strftime('%H%M%S', time.gmtime(time.time() - interval))

        # decode it
        res = subprocess.run(["jt9", "--" + mode, decode_file], capture_output=True)
        out = res.stdout.decode()

        for line in out.split("\n"):
            if line[:6] == "000000":
                msg = f"{mode} {stamp} {line[7:]}"
                print(msg)
                self.all_txt.write(msg + "\n")
                self.all_txt.flush()

    def rotate_ft8(self, msg):
        self.rotate_and_decode("ft8", self.tb.ft8_sink, 15)

    def rotate_ft4(self, msg):
        self.rotate_and_decode("ft4", self.tb.ft4_sink, 7.5)

if __name__ == "__main__":
    b = blk()
    b.rotate('foo')

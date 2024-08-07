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

        # remember if we saw decodes in the last cycle
        self.decode = { 'ft8': False, 'ft4': False }

    def start(self):
        # store all decodes in file in PWD
        self.all_txt = open("ft84.txt", "a")
        self.conn = None
        self.cur = None

        # change to tmp_path (jt9 leaves a few temp files around there)
        try: os.mkdir(self.tmp_path)
        except: pass
        os.chdir(self.tmp_path)

    def handle_line(self, mode, stamp, line):
        # jt9 out: 000000   3  0.3 1743 ~  CQ DF7CB JO31
        # ALL.TXT: 220321_131530  2400.040 Rx FT8      1  0.5  523 ES2KO LY1FX 73
        fields = line.split(None, 5)
        if len(fields) > 5 and fields[0] == "000000":
            try:
                db = int(fields[1])
                dt = float(fields[2])
                freq = int(fields[3])
                prefix = f"{stamp} 2400.040 Rx {mode.upper()}"
                data = f" {db:+3} {dt:+4} {freq:4} "
                msg = fields[5].rstrip()

                # file output
                self.all_txt.write(prefix + data + msg + "\n")
                self.all_txt.flush()

                # terminal output
                if mode == 'ft8':
                    if stamp[-2:] in ('00', '30'):
                        stampcolor = "\033[48;5;39m"
                    else:
                        stampcolor = "\033[48;5;42m"
                elif mode == 'ft4':
                    if stamp[-2:] in ('00', '15', '30', '45'):
                        stampcolor = "\033[48;5;208m"
                    else:
                        stampcolor = "\033[48;5;220m"
                if msg.startswith("DF7CB "): # received my call
                    start, end = "\033[48;5;226m", "\033[0m"
                elif "DF7CB" in msg: # sent by myself
                    start, end = "\033[41m", "\033[0m"
                else:
                    start, end = "", ""
                print(f"{stampcolor}{prefix}\033[0m{data}{start}{msg}{end}", flush=True)

                return True # successful decode
            except:
                pass
        return False

    def rotate_and_decode(self, mode, sink, interval):
        tmp_file = f"{mode}-tmp.wav"
        decode_file = f"{mode}.wav"

        # rotate file
        try: os.unlink(decode_file)
        except: pass
        try: os.rename(tmp_file, decode_file)
        except: pass

        # ask sink to re-open file
        sink.open(tmp_file)

        stamp = time.strftime('%F_%H%M%S', time.gmtime(time.time() - interval))

        # decode it
        res = subprocess.run(["jt9", "--" + mode, decode_file], capture_output=True)
        out = res.stdout.decode()

        decode = False
        for line in out.split("\n"):
            # decode a line
            decode |= self.handle_line(mode, stamp, line)

        # insert a separator line if we saw something in the last cycle, but this cycle was empty
        if not decode and self.decode[mode]:
            print(flush=True)
        self.decode[mode] = decode

    def rotate_ft8(self, msg):
        self.rotate_and_decode("ft8", self.tb.ft8_sink, 15)

    def rotate_ft4(self, msg):
        self.rotate_and_decode("ft4", self.tb.ft4_sink, 7.5)

from gnuradio import gr
import pmt
import os
import subprocess
import time
import psycopg2
import re

class blk(gr.basic_block):
    """Rotate wav files and feed them to jt9 for FT8 and FT4 decoding"""

    def __init__(self, tmp_path='.', PG_conn=''):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Rotate and Decode Wav File',   # will show up in GRC
            in_sig=None,
            out_sig=None,
        )
        self.tmp_path = tmp_path
        self.pg_conn = PG_conn

        self.message_port_register_in(pmt.intern("rotate_ft8"))
        self.set_msg_handler(pmt.intern("rotate_ft8"), self.rotate_ft8)
        self.message_port_register_in(pmt.intern("rotate_ft4"))
        self.set_msg_handler(pmt.intern("rotate_ft4"), self.rotate_ft4)

    def start(self):
        # store all decodes in file in PWD
        self.all_txt = open("ft84.txt", "a")
        self.conn = None
        self.cur = None

        # change to tmp_path (jt9 leaves a few temp files around there)
        try: os.mkdir(self.tmp_path)
        except: pass
        os.chdir(self.tmp_path)

    def query(self, *args):
        if not self.conn:
            try:
                self.conn = psycopg2.connect(self.pg_conn)
                self.conn.autocommit = True
                self.cur = self.conn.cursor()
            except Exception as e:
                print(e)
                return
        self.cur.execute(*args)
        return self.cur

    def handle_line(self, mode, stamp, line):
        """000000   3  0.3 1743 ~  CQ DF7CB JO31"""
        fields = line.split(None, 5)
        if len(fields) > 5 and fields[0] == "000000":

            # start timestamptz,
            # qrg numeric,
            # rx text,
            # mode text,
            # rst int,
            # off numeric, -- time offset
            # freq int,
            # msg text,

            msg = fields[5].rstrip()
            self.query("""insert into all_txt values(%s, %s, %s, %s, %s, %s, %s, %s) on conflict do nothing""", (stamp, 2400.040, 'Rx', mode.upper(), fields[1], fields[2], fields[3], msg))

            call_re = '<?(?:([A-Z0-9/]+)|\.\.\.)>?' # also matches CQ
            loc_rrr_re = '(?:([A-R]{2}[0-9]{2})|R?[+-][0-9]+|RRR|73)' # only loc captured

            if m := re.match(f"{call_re} {call_re} {loc_rrr_re}\\b", msg):
                dx, call, loc = m.group(1), m.group(2), m.group(3)

                if dx == 'DF7CB':
                    print("\033[1;33m", end='')

                if call == "DF7CB":
                    print("\033[41m", end='')
                elif call:
                    logged = self.query("""select call from log where call = %s and mode in ('FT8', 'FT4') and qrg::band = '13cm'""", (call,)).fetchone()
                    if not logged:
                        print("\033[46mNew call", call)

                if loc and loc != "RR73":
                    logged = self.query("""select call from log where loc::varchar(4) = %s and mode in ('FT8', 'FT4') and qrg::band = '13cm'""", (loc,)).fetchone()
                    if not logged:
                        print("\033[43mNew loc", loc)

            else:
                print("Unknown format: ", end='')

            out = f"{mode} {stamp} {line[7:]}"
            self.all_txt.write(out + "\n")
            self.all_txt.flush()
            print(out, end="\033[0m\n")

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

        stamp = time.strftime('%F %H%M%S', time.gmtime(time.time() - interval))

        # decode it
        res = subprocess.run(["jt9", "--" + mode, decode_file], capture_output=True)
        out = res.stdout.decode()

        for line in out.split("\n"):
            self.handle_line(mode, stamp, line)

    def rotate_ft8(self, msg):
        self.rotate_and_decode("ft8", self.tb.ft8_sink, 15)

    def rotate_ft4(self, msg):
        self.rotate_and_decode("ft4", self.tb.ft4_sink, 7.5)

if __name__ == "__main__":
    b = blk()
    b.rotate('foo')

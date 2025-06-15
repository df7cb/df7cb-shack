from gnuradio import gr
import pmt

import socket
import threading
import re

class Client(threading.Thread):
    def __init__(self, sock, address, block):
        threading.Thread.__init__(self)
        self.socket = sock
        self.address = address
        self.block = block

        self.band = 2_400_000_000 # remember the band the client wants to be on
        self.mode = "USB"

    def reply(self, msg):
        self.socket.sendall((msg + "\r\n").encode("UTF-8"))

    def run(self):
        try:
            while True:
                data = self.socket.recv(128)
                if len(data) == 0: break

                cmd = str(data.decode("utf-8")).strip()
                #print("rigctld:", cmd)

                if cmd == "":
                    pass
                elif m := re.match(r"f\b", cmd):
                    freq = self.band + self.block.freq
                    if self.mode == "CW":
                        freq += 850
                    self.reply(str(freq))
                elif m := re.match(r"F\s*(\d+)\b", cmd):
                    freq = int(m.group(1))
                    if self.mode == "CW":
                        freq -= 850
                    base_freq = freq % 500_000
                    self.band = freq - base_freq
                    self.block.message_port_pub(pmt.intern("freq_out"),
                                                pmt.cons(pmt.intern('control_change'), pmt.from_long(base_freq)))
                    self.reply("RPRT 0")
                elif m := re.match(r"l\s*KEYSPD\b", cmd):
                    self.reply(str(self.block.wpm))
                elif m := re.match(r"m\b", cmd):
                    self.reply(self.mode)
                    self.reply("3000")
                elif m := re.match(r"M\s*(\S+)\s+.+\b", cmd):
                    self.mode = m.group(1)
                    self.reply("RPRT 0")
                elif m := re.match(r"s\b", cmd): # split mode
                    self.reply("0")
                    self.reply("None")
                elif m := re.match(r"v\b", cmd):
                    self.reply("VFOA")
                elif m := re.match(r"V\s*.+\b", cmd):
                    self.reply("RPRT 0")
                elif m := re.match(r"\\chk_vfo\b", cmd):
                    self.reply("0")
                elif m := re.match(r"\\get_lock_mode\b", cmd):
                    self.reply("0")
                    self.reply("RPRT 0")
                elif m := re.match(r"\\get_powerstat\b", cmd):
                    self.reply("1")
                elif m := re.match(r"\\dump_state\b", cmd):
                    self.reply("""\
1
1
0
150000.000000 1500000000.000000 0x1ff -1 -1 0x17e00007 0xf
0 0 0 0 0 0 0
150000.000000 1500000000.000000 0x1ff 5000 100000 0x17e00007 0xf
0 0 0 0 0 0 0
0x1ff 1
0x1ff 0
0 0
0xc 2400
0xc 1800
0xc 3000
0xc 0
0x2 500
0x2 2400
0x2 50
0x2 0
0x10 300
0x10 2400
0x10 50
0x10 0
0x1 8000
0x1 2400
0x1 10000
0x20 15000
0x20 8000
0x40 230000
0 0
9990
9990
10000
0
10 
10 20 30 
0xffffffffffffffff
0xffffffffffffffff
0xfffffffff7ffffff
0xfffeff7083ffffff
0xffffffffffffffff
0xffffffffffffffbf""")
                    self.reply("done")
                else:
                    print("Unknown rigctld command:", cmd)
                    self.reply("RPRT -1")
        except Exception as inst:
            print(inst)
            pass

        print("rigctld: client " + str(self.address) + " has disconnected")

def newConnections(socket, block):
    #connections = []
    #total_connections = 0

    while True:
        sock, address = socket.accept()
        print("rigctld: new connection from", address)
        Client(sock, address, block).start()

class blk(gr.sync_block):
    """Hamlib rigctld interface block"""

    def __init__(self, port=4536):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Hamlib rigctld interface',
            in_sig=None,
            out_sig=None,
        )

        self.port = port

        self.freq = 0
        self.wpm = 0

        self.message_port_register_in(pmt.intern("freq_in"))
        self.set_msg_handler(pmt.intern("freq_in"), self.freq_in)
        self.message_port_register_in(pmt.intern("wpm_in"))
        self.set_msg_handler(pmt.intern("wpm_in"), self.wpm_in)

        self.message_port_register_out(pmt.intern("freq_out"))

        self.tcpthread = threading.Thread(target=self.tcp, daemon=True)
        self.tcpthread.start()

    #def start(self):

    def freq_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('freq'):
            self.freq = int(pmt.to_double(pmt.cdr(msg)))

    def wpm_in(self, msg):
        if msg.is_pair() and pmt.car(msg) == pmt.intern('value'):
            self.wpm = int(pmt.to_double(pmt.cdr(msg)))

    def tcp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("localhost", self.port))
        sock.listen(5)

        newConnectionsThread = threading.Thread(target = newConnections, args = (sock, self))
        newConnectionsThread.start()

if __name__ == '__main__':
    blk()

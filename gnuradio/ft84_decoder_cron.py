from gnuradio import gr
import pmt
import time
import threading

class blk(gr.basic_block):
    """Send Timed Msgs"""

    def __init__(self):
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Send Timed Msgs',   # will show up in GRC
            in_sig=None,
            out_sig=None,
        )
        self.message_port_register_out(pmt.intern("cron_ft8"))
        self.message_port_register_out(pmt.intern("cron_ft4"))

    def start(self):
        self.cron_thread = threading.Thread(target=self.cron_ft8, daemon=True)
        self.cron_thread.start()
        self.cron_thread = threading.Thread(target=self.cron_ft4, daemon=True)
        self.cron_thread.start()

    def sleep(self, interval):
        time.sleep(interval - (time.time() % interval))
        return True

    def cron_ft8(self):
        while self.sleep(15):
            self.message_port_pub(pmt.intern("cron_ft8"), pmt.intern("rotate_ft8"))

    def cron_ft4(self):
        while self.sleep(7.5):
            self.message_port_pub(pmt.intern("cron_ft4"), pmt.intern("rotate_ft4"))

if __name__ == "__main__":
    b = blk()
    b.cron_ft8()

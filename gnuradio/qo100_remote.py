#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: qo100
# Author: DF7CB
# GNU Radio version: 3.10.12.0

from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import zeromq
import limesdr
import threading




class qo100_remote(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "qo100", catch_exceptions=True)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.decim = decim = 11
        self.zmq_watermark = zmq_watermark = 4
        self.samp_rate = samp_rate = decim*48000

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_push_sink_0 = zeromq.push_sink(gr.sizeof_gr_complex, 1, 'tcp://0.0.0.0:10010', 100, False, zmq_watermark, True)
        self.zeromq_pull_source_0 = zeromq.pull_source(gr.sizeof_gr_complex, 1, 'tcp://192.168.0.191:10024', 100, False, zmq_watermark, False)
        self.limesdr_source = limesdr.source('', 0, '', False)


        self.limesdr_source.set_sample_rate(samp_rate)


        self.limesdr_source.set_center_freq(739.75e6, 0)

        self.limesdr_source.set_bandwidth(1.5e6, 0)




        self.limesdr_source.set_gain(30, 0)


        self.limesdr_source.set_antenna(2, 0)


        self.limesdr_source.calibrate(5e6, 0)
        self.limesdr_sink = limesdr.sink('', 0, '', '')


        self.limesdr_sink.set_sample_rate(samp_rate)


        self.limesdr_sink.set_center_freq(2400.250e6, 0)

        self.limesdr_sink.set_bandwidth(5e6, 0)




        self.limesdr_sink.set_gain(73, 0)


        self.limesdr_sink.set_antenna(2, 0)


        self.limesdr_sink.calibrate(2.5e6, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.limesdr_source, 0), (self.zeromq_push_sink_0, 0))
        self.connect((self.zeromq_pull_source_0, 0), (self.limesdr_sink, 0))


    def get_decim(self):
        return self.decim

    def set_decim(self, decim):
        self.decim = decim
        self.set_samp_rate(self.decim*48000)

    def get_zmq_watermark(self):
        return self.zmq_watermark

    def set_zmq_watermark(self, zmq_watermark):
        self.zmq_watermark = zmq_watermark

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate




def main(top_block_cls=qo100_remote, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()
    tb.flowgraph_started.set()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()

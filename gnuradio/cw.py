#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: CW Generator
# Author: DF7CB
# GNU Radio version: 3.10.0.0

from gnuradio import analog
from gnuradio import audio
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import cw_cw_modulator as cw_modulator  # embedded python block
import cw_cw_source as cw_source  # embedded python block




class cw(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "CW Generator", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48e3

        ##################################################
        # Blocks
        ##################################################
        self.pitch_source = analog.sig_source_f(samp_rate, analog.GR_COS_WAVE, 850, 1, 0, 0)
        self.cw_source = cw_source.blk(port='/dev/ttyUSBK3NG')
        self.cw_modulator = cw_modulator.blk()
        self.cw_audio_sink = audio.sink(48000, 'pulse:tx0', True)
        self.band_pass_filter_0 = filter.fir_filter_fff(
            1,
            firdes.band_pass(
                1,
                samp_rate,
                750,
                950,
                50,
                window.WIN_HAMMING,
                6.76))


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.cw_source, 'cw_out'), (self.cw_modulator, 'cw_in'))
        self.connect((self.band_pass_filter_0, 0), (self.cw_audio_sink, 0))
        self.connect((self.cw_modulator, 0), (self.band_pass_filter_0, 0))
        self.connect((self.pitch_source, 0), (self.cw_modulator, 0))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.band_pass_filter_0.set_taps(firdes.band_pass(1, self.samp_rate, 750, 950, 50, window.WIN_HAMMING, 6.76))
        self.pitch_source.set_sampling_freq(self.samp_rate)




def main(top_block_cls=cw, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start(500)

    tb.wait()


if __name__ == '__main__':
    main()

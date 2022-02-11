#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: FT8 and FT4 Decoder
# Author: DF7CB
# Copyright: GPL-3+
# GNU Radio version: 3.10.0.0

from gnuradio import audio
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import ft84_decoder_cron as cron  # embedded python block
import ft84_decoder_rotate as rotate  # embedded python block


def snipfcn_ft84_init(self):
    import os

    # make top block accessible in rotate block
    self.rotate.tb = self

    # change to temp dir
    self.dir = '/run/user/1000/gnuradio'
    try: os.mkdir(self.dir)
    except: pass
    os.chdir(self.dir)


def snippets_main_after_init(tb):
    snipfcn_ft84_init(tb)


class ft84_decoder(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "FT8 and FT4 Decoder", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 48e3

        ##################################################
        # Blocks
        ##################################################
        self.rotate = rotate.blk()
        self.rational_resampler_4 = filter.rational_resampler_fff(
                interpolation=1,
                decimation=4,
                taps=[],
                fractional_bw=0)
        self.ft8_sink = blocks.wavfile_sink(
            '/dev/null',
            1,
            12000,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.ft4_sink = blocks.wavfile_sink(
            '/dev/null',
            1,
            12000,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.cron = cron.blk()
        self.audio_source_rx2 = audio.source(48000, 'pulse:rx2.monitor', True)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.cron, 'cron_ft4'), (self.rotate, 'rotate_ft4'))
        self.msg_connect((self.cron, 'cron_ft8'), (self.rotate, 'rotate_ft8'))
        self.connect((self.audio_source_rx2, 0), (self.rational_resampler_4, 0))
        self.connect((self.rational_resampler_4, 0), (self.ft4_sink, 0))
        self.connect((self.rational_resampler_4, 0), (self.ft8_sink, 0))


    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate




def main(top_block_cls=ft84_decoder, options=None):
    tb = top_block_cls()
    snippets_main_after_init(tb)
    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    tb.wait()


if __name__ == '__main__':
    main()

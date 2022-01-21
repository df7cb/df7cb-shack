#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: qo100
# Author: DM6AS, DF7CB
# GNU Radio version: 3.10.0.0

from packaging.version import Version as StrictVersion

if __name__ == '__main__':
    import ctypes
    import sys
    if sys.platform.startswith('linux'):
        try:
            x11 = ctypes.cdll.LoadLibrary('libX11.so')
            x11.XInitThreads()
        except:
            print("Warning: failed to XInitThreads()")

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio.filter import firdes
import sip
from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import filter
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio.qtgui import Range, RangeWidget
from PyQt5 import QtCore
import limesdr



from gnuradio import qtgui

class qo100(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "qo100", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("qo100")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except:
            pass
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "qo100")

        try:
            if StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
                self.restoreGeometry(self.settings.value("geometry").toByteArray())
            else:
                self.restoreGeometry(self.settings.value("geometry"))
        except:
            pass

        ##################################################
        # Variables
        ##################################################
        self.decim = decim = 11
        self.vfo = vfo = 40
        self.samp_rate = samp_rate = decim*48e3
        self.mag = mag = 0.9
        self.af_gain = af_gain = 50

        ##################################################
        # Blocks
        ##################################################
        self._vfo_range = Range(-10, 510, 0.1, 40, 150)
        self._vfo_win = RangeWidget(self._vfo_range, self.set_vfo, "vfo", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._vfo_win, 14, 0, 1, 1)
        for r in range(14, 15):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._af_gain_range = Range(0, 200, 5, 50, 200)
        self._af_gain_win = RangeWidget(self._af_gain_range, self.set_af_gain, "af_gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._af_gain_win, 29, 0, 1, 1)
        for r in range(29, 30):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rational_resampler_xxx_0 = filter.rational_resampler_ccc(
                interpolation=decim,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_c(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            250e3, #fc
            samp_rate, #bw
            "", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.05)
        self.qtgui_waterfall_sink_x_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-75, -45)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._qtgui_waterfall_sink_x_0_win, 0, 0, 14, 1)
        for r in range(0, 14):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.qtgui_freq_sink_x_1 = qtgui.freq_sink_c(
            1024, #size
            window.WIN_HAMMING, #wintype
            0, #fc
            24e3, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_1.set_update_time(0.01)
        self.qtgui_freq_sink_x_1.set_y_axis(-86, -40)
        self.qtgui_freq_sink_x_1.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_1.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_1.enable_autoscale(False)
        self.qtgui_freq_sink_x_1.enable_grid(True)
        self.qtgui_freq_sink_x_1.set_fft_average(0.2)
        self.qtgui_freq_sink_x_1.enable_axis_labels(True)
        self.qtgui_freq_sink_x_1.enable_control_panel(True)
        self.qtgui_freq_sink_x_1.set_fft_window_normalized(True)

        self.qtgui_freq_sink_x_1.disable_legend()


        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_1.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_1.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_1.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_1_win = sip.wrapinstance(self.qtgui_freq_sink_x_1.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_freq_sink_x_1_win, 15, 0, 14, 1)
        for r in range(15, 29):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.limesdr_source_0 = limesdr.source('', 0, '')
        self.limesdr_source_0.set_sample_rate(samp_rate)
        self.limesdr_source_0.set_center_freq(739.75e6, 0)
        self.limesdr_source_0.set_bandwidth(1.5e6, 0)
        self.limesdr_source_0.set_gain(30,0)
        self.limesdr_source_0.set_antenna(2,0)
        self.limesdr_source_0.calibrate(5e6, 0)
        self.limesdr_sink_0 = limesdr.sink('', 0, '', '')
        self.limesdr_sink_0.set_sample_rate(samp_rate)
        self.limesdr_sink_0.set_center_freq(2400.250e6, 0)
        self.limesdr_sink_0.set_bandwidth(5e6,0)
        self.limesdr_sink_0.set_gain(73,0)
        self.limesdr_sink_0.set_antenna(2,0)
        self.limesdr_sink_0.calibrate(2.5e6, 0)
        self.blocks_swapiq_0 = blocks.swap_iq(1, gr.sizeof_gr_complex)
        self.blocks_multiply_xx_0_0_0_0_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_xx_0_0_0_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_xx_0_0_0 = blocks.multiply_vcc(1)
        self.blocks_multiply_const_vxx_1 = blocks.multiply_const_cc(0.01)
        self.blocks_float_to_complex_1_0 = blocks.float_to_complex(1)
        self.blocks_complex_to_float_0_0 = blocks.complex_to_float(1)
        self.blocks_complex_to_float_0 = blocks.complex_to_float(1)
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.band_pass_filter_0_0_1 = filter.fir_filter_ccc(
            2*decim,
            firdes.complex_band_pass(
                1,
                samp_rate,
                -12e3,
                12e3,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.band_pass_filter_0_0_0 = filter.fir_filter_ccc(
            decim,
            firdes.complex_band_pass(
                10,
                samp_rate,
                0,
                3000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.band_pass_filter_0_0 = filter.fir_filter_ccc(
            decim,
            firdes.complex_band_pass(
                af_gain,
                samp_rate,
                0,
                3000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.band_pass_filter_0 = filter.interp_fir_filter_ccc(
            1,
            firdes.complex_band_pass(
                1,
                48e3,
                0,
                5000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.audio_source_0 = audio.source(48000, 'pulse:tx0.monitor', True)
        self.audio_sink_0_0 = audio.sink(48000, 'pulse:rx2', True)
        self.audio_sink_0 = audio.sink(48000, 'pulse', True)
        self.analog_sig_source_x_0_0_0_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (250-40)*1e3, mag, 0, 0)
        self.analog_sig_source_x_0_0_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (250-vfo)*1e3, mag, 0, 0)
        self.analog_sig_source_x_0_0 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (vfo-250)*1e3, mag, 0, 0)
        self.analog_const_source_x_0 = analog.sig_source_f(0, analog.GR_CONST_WAVE, 0, 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_const_source_x_0, 0), (self.blocks_float_to_complex_1_0, 1))
        self.connect((self.analog_sig_source_x_0_0, 0), (self.blocks_multiply_xx_0_0_0, 1))
        self.connect((self.analog_sig_source_x_0_0_0, 0), (self.blocks_multiply_const_vxx_1, 0))
        self.connect((self.analog_sig_source_x_0_0_0, 0), (self.blocks_multiply_xx_0_0_0_0, 1))
        self.connect((self.analog_sig_source_x_0_0_0_0, 0), (self.blocks_multiply_xx_0_0_0_0_0, 1))
        self.connect((self.audio_source_0, 0), (self.blocks_float_to_complex_1_0, 0))
        self.connect((self.band_pass_filter_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.band_pass_filter_0_0, 0), (self.blocks_complex_to_float_0, 0))
        self.connect((self.band_pass_filter_0_0_0, 0), (self.blocks_complex_to_float_0_0, 0))
        self.connect((self.band_pass_filter_0_0_1, 0), (self.qtgui_freq_sink_x_1, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.blocks_complex_to_float_0, 0), (self.audio_sink_0, 0))
        self.connect((self.blocks_complex_to_float_0_0, 0), (self.audio_sink_0_0, 0))
        self.connect((self.blocks_float_to_complex_1_0, 0), (self.band_pass_filter_0, 0))
        self.connect((self.blocks_multiply_const_vxx_1, 0), (self.blocks_swapiq_0, 0))
        self.connect((self.blocks_multiply_xx_0_0_0, 0), (self.limesdr_sink_0, 0))
        self.connect((self.blocks_multiply_xx_0_0_0_0, 0), (self.band_pass_filter_0_0, 0))
        self.connect((self.blocks_multiply_xx_0_0_0_0, 0), (self.band_pass_filter_0_0_1, 0))
        self.connect((self.blocks_multiply_xx_0_0_0_0_0, 0), (self.band_pass_filter_0_0_0, 0))
        self.connect((self.blocks_swapiq_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.limesdr_source_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.limesdr_source_0, 0), (self.blocks_multiply_xx_0_0_0_0, 0))
        self.connect((self.limesdr_source_0, 0), (self.blocks_multiply_xx_0_0_0_0_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.blocks_multiply_xx_0_0_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "qo100")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_decim(self):
        return self.decim

    def set_decim(self, decim):
        self.decim = decim
        self.set_samp_rate(self.decim*48e3)

    def get_vfo(self):
        return self.vfo

    def set_vfo(self, vfo):
        self.vfo = vfo
        self.analog_sig_source_x_0_0.set_frequency((self.vfo-250)*1e3)
        self.analog_sig_source_x_0_0_0.set_frequency((250-self.vfo)*1e3)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_sig_source_x_0_0.set_sampling_freq(self.samp_rate)
        self.analog_sig_source_x_0_0_0.set_sampling_freq(self.samp_rate)
        self.analog_sig_source_x_0_0_0_0.set_sampling_freq(self.samp_rate)
        self.band_pass_filter_0_0.set_taps(firdes.complex_band_pass(self.af_gain, self.samp_rate, 0, 3000, 1000, window.WIN_HAMMING, 6.76))
        self.band_pass_filter_0_0_0.set_taps(firdes.complex_band_pass(10, self.samp_rate, 0, 3000, 1000, window.WIN_HAMMING, 6.76))
        self.band_pass_filter_0_0_1.set_taps(firdes.complex_band_pass(1, self.samp_rate, -12e3, 12e3, 1000, window.WIN_HAMMING, 6.76))
        self.qtgui_waterfall_sink_x_0.set_frequency_range(250e3, self.samp_rate)

    def get_mag(self):
        return self.mag

    def set_mag(self, mag):
        self.mag = mag
        self.analog_sig_source_x_0_0.set_amplitude(self.mag)
        self.analog_sig_source_x_0_0_0.set_amplitude(self.mag)
        self.analog_sig_source_x_0_0_0_0.set_amplitude(self.mag)

    def get_af_gain(self):
        return self.af_gain

    def set_af_gain(self, af_gain):
        self.af_gain = af_gain
        self.band_pass_filter_0_0.set_taps(firdes.complex_band_pass(self.af_gain, self.samp_rate, 0, 3000, 1000, window.WIN_HAMMING, 6.76))




def main(top_block_cls=qo100, options=None):

    if StrictVersion("4.5.0") <= StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()

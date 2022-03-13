#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: qo100
# Author: DM6AS, DF7CB
# GNU Radio version: 3.10.1.1

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
import qo100_control as control  # embedded python block
import qo100_midi_block as midi_block  # embedded python block


def snipfcn_inject_tb(self):
    self.control.tb = self


def snippets_main_after_init(tb):
    snipfcn_inject_tb(tb)

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
        self.vfo = vfo = 40e3
        self.tx_vfo = tx_vfo = 40e3

        self.tx_power = tx_power = 1.0
        self.samp_rate = samp_rate = decim*48e3
        self.rx0_low_cutoff = rx0_low_cutoff = 0
        self.rx0_high_cutoff = rx0_high_cutoff = 3000
        self.mag = mag = 0.9


        self.af_gain = af_gain = 20

        ##################################################
        # Blocks
        ##################################################
        self._vfo_msgdigctl_win = qtgui.MsgDigitalNumberControl(lbl = 'RX', min_freq_hz = -10e3, max_freq_hz=510e3, parent=self,  thousands_separator=".",background_color="black",fontColor="white", var_callback=self.set_vfo,outputmsgname="'freq'".replace("'",""))
        self._vfo_msgdigctl_win.setValue(40e3)
        self._vfo_msgdigctl_win.setReadOnly(False)
        self.vfo = self._vfo_msgdigctl_win

        self.top_layout.addWidget(self._vfo_msgdigctl_win)
        self._tx_vfo_msgdigctl_win = qtgui.MsgDigitalNumberControl(lbl = 'TX', min_freq_hz = -10e3, max_freq_hz=510e3, parent=self,  thousands_separator=".",background_color="black",fontColor="white", var_callback=self.set_tx_vfo,outputmsgname="'freq'".replace("'",""))
        self._tx_vfo_msgdigctl_win.setValue(40e3)
        self._tx_vfo_msgdigctl_win.setReadOnly(False)
        self.tx_vfo = self._tx_vfo_msgdigctl_win

        self.top_layout.addWidget(self._tx_vfo_msgdigctl_win)
        self._af_gain_range = Range(0, 200, 5, 20, 200)
        self._af_gain_win = RangeWidget(self._af_gain_range, self.set_af_gain, "af_gain", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._af_gain_win, 29, 0, 1, 1)
        for r in range(29, 30):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.vfo2_to_float = blocks.complex_to_float(1)
        self.vfo2_signal_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 250e3-40e3, mag, 0, 0)
        self.vfo2_mixer = blocks.multiply_vcc(1)
        self.vfo2_bandpass = filter.fir_filter_ccc(
            decim,
            firdes.complex_band_pass(
                10,
                samp_rate,
                0,
                5000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.vfo2_audio_sink = audio.sink(48000, 'pulse:rx2', False)
        self.vfo0_waterfall_atten = blocks.multiply_const_cc(0.01)
        self.vfo0_waterfall_add = blocks.add_vcc(1)
        self.vfo0_to_float = blocks.complex_to_float(1)
        self.vfo0_spectrum = qtgui.freq_sink_c(
            1024, #size
            window.WIN_HAMMING, #wintype
            40e3, #fc
            24e3, #bw
            '', #name
            1,
            None # parent
        )
        self.vfo0_spectrum.set_update_time(0.01)
        self.vfo0_spectrum.set_y_axis(-86, -40)
        self.vfo0_spectrum.set_y_label('Relative Gain', 'dB')
        self.vfo0_spectrum.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.vfo0_spectrum.enable_autoscale(False)
        self.vfo0_spectrum.enable_grid(True)
        self.vfo0_spectrum.set_fft_average(0.2)
        self.vfo0_spectrum.enable_axis_labels(True)
        self.vfo0_spectrum.enable_control_panel(True)
        self.vfo0_spectrum.set_fft_window_normalized(True)

        self.vfo0_spectrum.disable_legend()


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
                self.vfo0_spectrum.set_line_label(i, "Data {0}".format(i))
            else:
                self.vfo0_spectrum.set_line_label(i, labels[i])
            self.vfo0_spectrum.set_line_width(i, widths[i])
            self.vfo0_spectrum.set_line_color(i, colors[i])
            self.vfo0_spectrum.set_line_alpha(i, alphas[i])

        self._vfo0_spectrum_win = sip.wrapinstance(self.vfo0_spectrum.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._vfo0_spectrum_win, 15, 0, 14, 1)
        for r in range(15, 29):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.vfo0_signal_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 250e3-vfo, mag, 0, 0)
        self.vfo0_scope_bandpass = filter.fir_filter_ccc(
            2*decim,
            firdes.complex_band_pass(
                1,
                samp_rate,
                -12e3,
                12e3,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.vfo0_mixer = blocks.multiply_vcc(1)
        self.vfo0_bandpass = filter.fir_filter_ccc(
            decim,
            firdes.complex_band_pass(
                af_gain,
                samp_rate,
                rx0_low_cutoff,
                rx0_high_cutoff,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.vfo0_audio_sink = audio.sink(48000, 'pulse', False)
        self.tx_vfo_signal_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, tx_vfo - 250e3, mag, 0, 0)
        self.tx_to_complex = blocks.float_to_complex(1)
        self.tx_power_to_msg = blocks.var_to_msg_pair('value')
        if "real" == "int":
        	isFloat = False
        	scaleFactor = 1
        else:
        	isFloat = True
        	scaleFactor = 100

        _tx_power_gauge_lg_win = qtgui.GrLevelGauge('TX Power',"default","default","default",0,100, 100, False,1,isFloat,scaleFactor,True,self)
        _tx_power_gauge_lg_win.setValue(1.0)
        self.tx_power_gauge = _tx_power_gauge_lg_win

        self.top_layout.addWidget(_tx_power_gauge_lg_win)
        self.tx_mixer = blocks.multiply_vcc(1)
        self.tx_bandpass = filter.interp_fir_filter_ccc(
            1,
            firdes.complex_band_pass(
                tx_power,
                48e3,
                0,
                3000,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.tx_audio_source = audio.source(48000, 'pulse:tx0.monitor', False)
        self.rx_waterfall = qtgui.waterfall_sink_c(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            250e3, #fc
            samp_rate, #bw
            "", #name
            1, #number of inputs
            None # parent
        )
        self.rx_waterfall.set_update_time(0.05)
        self.rx_waterfall.enable_grid(False)
        self.rx_waterfall.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.rx_waterfall.set_line_label(i, "Data {0}".format(i))
            else:
                self.rx_waterfall.set_line_label(i, labels[i])
            self.rx_waterfall.set_color_map(i, colors[i])
            self.rx_waterfall.set_line_alpha(i, alphas[i])

        self.rx_waterfall.set_intensity_range(-75, -45)

        self._rx_waterfall_win = sip.wrapinstance(self.rx_waterfall.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._rx_waterfall_win, 0, 0, 14, 1)
        for r in range(0, 14):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rx_resampler = filter.rational_resampler_ccc(
                interpolation=decim,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.rx0_low_cutoff_to_msg = blocks.var_to_msg_pair('value')
        self.rx0_high_cutoff_to_msg = blocks.var_to_msg_pair('value')
        self.midi_block = midi_block.blk(midi_port='DJControl Compact:DJControl Compact DJControl Com')
        if "int" == "int":
        	isFloat = False
        	scaleFactor = 1
        else:
        	isFloat = True
        	scaleFactor = 1

        _low_cutoff_gauge_lg_win = qtgui.GrLevelGauge('',"default","default","default",0,3000, 100, False,1,isFloat,scaleFactor,True,self)
        _low_cutoff_gauge_lg_win.setValue(0)
        self.low_cutoff_gauge = _low_cutoff_gauge_lg_win

        self.top_layout.addWidget(_low_cutoff_gauge_lg_win)
        self.limesdr_source = limesdr.source('', 0, '')
        self.limesdr_source.set_sample_rate(samp_rate)
        self.limesdr_source.set_center_freq(739.75e6, 0)
        self.limesdr_source.set_bandwidth(1.5e6, 0)
        self.limesdr_source.set_gain(30,0)
        self.limesdr_source.set_antenna(2,0)
        self.limesdr_source.calibrate(5e6, 0)
        self.limesdr_sink = limesdr.sink('', 0, '', '')
        self.limesdr_sink.set_sample_rate(samp_rate)
        self.limesdr_sink.set_center_freq(2400.250e6, 0)
        self.limesdr_sink.set_bandwidth(5e6,0)
        self.limesdr_sink.set_gain(73,0)
        self.limesdr_sink.set_antenna(2,0)
        self.limesdr_sink.calibrate(2.5e6, 0)
        if "int" == "int":
        	isFloat = False
        	scaleFactor = 1
        else:
        	isFloat = True
        	scaleFactor = 1

        _high_cutoff_gauge_lg_win = qtgui.GrLevelGauge('',"default","default","default",0,3000, 100, False,1,isFloat,scaleFactor,True,self)
        _high_cutoff_gauge_lg_win.setValue(3000)
        self.high_cutoff_gauge = _high_cutoff_gauge_lg_win

        self.top_layout.addWidget(_high_cutoff_gauge_lg_win)
        self.control = control.blk()
        self.blocks_swapiq_0 = blocks.swap_iq(1, gr.sizeof_gr_complex)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.control, 'midi_out'), (self.midi_block, 'midi_in'))
        self.msg_connect((self.control, 'tx_freq_out'), (self.tx_vfo, 'valuein'))
        self.msg_connect((self.control, 'rx_freq_out'), (self.vfo, 'valuein'))
        self.msg_connect((self.midi_block, 'midi_out'), (self.control, 'midi_in'))
        self.msg_connect((self.rx0_high_cutoff_to_msg, 'msgout'), (self.high_cutoff_gauge, 'value'))
        self.msg_connect((self.rx0_low_cutoff_to_msg, 'msgout'), (self.low_cutoff_gauge, 'value'))
        self.msg_connect((self.rx_waterfall, 'freq'), (self.vfo, 'valuein'))
        self.msg_connect((self.tx_power_to_msg, 'msgout'), (self.tx_power_gauge, 'value'))
        self.msg_connect((self.tx_vfo, 'valueout'), (self.control, 'tx_freq_in'))
        self.msg_connect((self.vfo, 'valueout'), (self.control, 'rx_freq_in'))
        self.msg_connect((self.vfo, 'valueout'), (self.vfo0_spectrum, 'freq'))
        self.msg_connect((self.vfo0_spectrum, 'freq'), (self.vfo, 'valuein'))
        self.msg_connect((self.vfo0_spectrum, 'freq'), (self.vfo0_spectrum, 'freq'))
        self.connect((self.blocks_swapiq_0, 0), (self.vfo0_waterfall_atten, 0))
        self.connect((self.limesdr_source, 0), (self.vfo0_mixer, 0))
        self.connect((self.limesdr_source, 0), (self.vfo0_waterfall_add, 0))
        self.connect((self.limesdr_source, 0), (self.vfo2_mixer, 0))
        self.connect((self.rx_resampler, 0), (self.tx_mixer, 0))
        self.connect((self.tx_audio_source, 0), (self.tx_to_complex, 0))
        self.connect((self.tx_bandpass, 0), (self.rx_resampler, 0))
        self.connect((self.tx_mixer, 0), (self.limesdr_sink, 0))
        self.connect((self.tx_to_complex, 0), (self.tx_bandpass, 0))
        self.connect((self.tx_vfo_signal_source, 0), (self.tx_mixer, 1))
        self.connect((self.vfo0_bandpass, 0), (self.vfo0_to_float, 0))
        self.connect((self.vfo0_mixer, 0), (self.vfo0_bandpass, 0))
        self.connect((self.vfo0_mixer, 0), (self.vfo0_scope_bandpass, 0))
        self.connect((self.vfo0_scope_bandpass, 0), (self.vfo0_spectrum, 0))
        self.connect((self.vfo0_signal_source, 0), (self.blocks_swapiq_0, 0))
        self.connect((self.vfo0_signal_source, 0), (self.vfo0_mixer, 1))
        self.connect((self.vfo0_to_float, 0), (self.vfo0_audio_sink, 0))
        self.connect((self.vfo0_waterfall_add, 0), (self.rx_waterfall, 0))
        self.connect((self.vfo0_waterfall_atten, 0), (self.vfo0_waterfall_add, 1))
        self.connect((self.vfo2_bandpass, 0), (self.vfo2_to_float, 0))
        self.connect((self.vfo2_mixer, 0), (self.vfo2_bandpass, 0))
        self.connect((self.vfo2_signal_source, 0), (self.vfo2_mixer, 1))
        self.connect((self.vfo2_to_float, 0), (self.vfo2_audio_sink, 0))


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
        self.vfo0_signal_source.set_frequency(250e3-self.vfo)

    def get_tx_vfo(self):
        return self.tx_vfo

    def set_tx_vfo(self, tx_vfo):
        self.tx_vfo = tx_vfo
        self.tx_vfo_signal_source.set_frequency(self.tx_vfo - 250e3)

    def get_tx_power_gauge(self):
        return self.tx_power_gauge

    def set_tx_power_gauge(self, tx_power_gauge):
        self.tx_power_gauge = tx_power_gauge
        self.tx_power_gauge.setValue(1.0)

    def get_tx_power(self):
        return self.tx_power

    def set_tx_power(self, tx_power):
        self.tx_power = tx_power
        self.tx_bandpass.set_taps(firdes.complex_band_pass(self.tx_power, 48e3, 0, 3000, 1000, window.WIN_HAMMING, 6.76))
        self.tx_power_to_msg.variable_changed(self.tx_power)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rx_waterfall.set_frequency_range(250e3, self.samp_rate)
        self.tx_vfo_signal_source.set_sampling_freq(self.samp_rate)
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(self.af_gain, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 1000, window.WIN_HAMMING, 6.76))
        self.vfo0_scope_bandpass.set_taps(firdes.complex_band_pass(1, self.samp_rate, -12e3, 12e3, 1000, window.WIN_HAMMING, 6.76))
        self.vfo0_signal_source.set_sampling_freq(self.samp_rate)
        self.vfo2_bandpass.set_taps(firdes.complex_band_pass(10, self.samp_rate, 0, 5000, 1000, window.WIN_HAMMING, 6.76))
        self.vfo2_signal_source.set_sampling_freq(self.samp_rate)

    def get_rx0_low_cutoff(self):
        return self.rx0_low_cutoff

    def set_rx0_low_cutoff(self, rx0_low_cutoff):
        self.rx0_low_cutoff = rx0_low_cutoff
        self.rx0_low_cutoff_to_msg.variable_changed(self.rx0_low_cutoff)
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(self.af_gain, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 1000, window.WIN_HAMMING, 6.76))

    def get_rx0_high_cutoff(self):
        return self.rx0_high_cutoff

    def set_rx0_high_cutoff(self, rx0_high_cutoff):
        self.rx0_high_cutoff = rx0_high_cutoff
        self.rx0_high_cutoff_to_msg.variable_changed(self.rx0_high_cutoff)
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(self.af_gain, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 1000, window.WIN_HAMMING, 6.76))

    def get_mag(self):
        return self.mag

    def set_mag(self, mag):
        self.mag = mag
        self.tx_vfo_signal_source.set_amplitude(self.mag)
        self.vfo0_signal_source.set_amplitude(self.mag)
        self.vfo2_signal_source.set_amplitude(self.mag)

    def get_low_cutoff_gauge(self):
        return self.low_cutoff_gauge

    def set_low_cutoff_gauge(self, low_cutoff_gauge):
        self.low_cutoff_gauge = low_cutoff_gauge
        self.low_cutoff_gauge.setValue(0)

    def get_high_cutoff_gauge(self):
        return self.high_cutoff_gauge

    def set_high_cutoff_gauge(self, high_cutoff_gauge):
        self.high_cutoff_gauge = high_cutoff_gauge
        self.high_cutoff_gauge.setValue(3000)

    def get_af_gain(self):
        return self.af_gain

    def set_af_gain(self, af_gain):
        self.af_gain = af_gain
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(self.af_gain, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 1000, window.WIN_HAMMING, 6.76))




def main(top_block_cls=qo100, options=None):

    if StrictVersion("4.5.0") <= StrictVersion(Qt.qVersion()) < StrictVersion("5.0.0"):
        style = gr.prefs().get_string('qtgui', 'style', 'raster')
        Qt.QApplication.setGraphicsSystem(style)
    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()
    snippets_main_after_init(tb)
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

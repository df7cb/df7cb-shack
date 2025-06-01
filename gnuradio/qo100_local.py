#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: qo100
# Author: DM6AS, DF7CB
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import zeromq
import qo100_local_control as control  # embedded python block
import qo100_local_ft84_cron as ft84_cron  # embedded python block
import qo100_local_ft84_rotate as ft84_rotate  # embedded python block
import qo100_local_midi_block as midi_block  # embedded python block
import sip
import threading


def snipfcn_inject_tb(self):
    # make top block accessible in control block
    self.control.tb = self
    # make top block accessible in ft84_rotate block
    self.ft84_rotate.tb = self


def snippets_main_after_init(tb):
    snipfcn_inject_tb(tb)

class qo100_local(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "qo100", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("qo100")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "qo100_local")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.decim = decim = 11
        self.zmq_watermark = zmq_watermark = 4
        self.vfo = vfo = 40e3
        self.tx_vfo = tx_vfo = 40e3
        self.tx_power = tx_power = 1.0
        self.samp_rate = samp_rate = decim*48e3
        self.rx0_low_cutoff = rx0_low_cutoff = 0
        self.rx0_high_cutoff = rx0_high_cutoff = 3000





        self.mag = mag = 0.9



        ##################################################
        # Blocks
        ##################################################

        self._vfo_msgdigctl_win = qtgui.MsgDigitalNumberControl(lbl='RX', min_freq_hz=-10e3, max_freq_hz=510e3, parent=self, thousands_separator=".", background_color="black", fontColor="white", var_callback=self.set_vfo, outputmsgname='freq')
        self._vfo_msgdigctl_win.setValue(40e3)
        self._vfo_msgdigctl_win.setReadOnly(False)
        self.vfo = self._vfo_msgdigctl_win

        self.top_grid_layout.addWidget(self._vfo_msgdigctl_win, 39, 0, 1, 1)
        for r in range(39, 40):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._tx_vfo_msgdigctl_win = qtgui.MsgDigitalNumberControl(lbl='TX', min_freq_hz=-10e3, max_freq_hz=510e3, parent=self, thousands_separator=".", background_color="black", fontColor="white", var_callback=self.set_tx_vfo, outputmsgname='freq')
        self._tx_vfo_msgdigctl_win.setValue(40e3)
        self._tx_vfo_msgdigctl_win.setReadOnly(False)
        self.tx_vfo = self._tx_vfo_msgdigctl_win

        self.top_grid_layout.addWidget(self._tx_vfo_msgdigctl_win, 40, 0, 2, 1)
        for r in range(40, 42):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.zeromq_push_sink_0 = zeromq.push_sink(gr.sizeof_gr_complex, 1, 'tcp://0.0.0.0:10024', 100, False, zmq_watermark, True)
        self.zeromq_pull_source_0 = zeromq.pull_source(gr.sizeof_gr_complex, 1, 'tcp://192.168.0.11:10010', 100, False, zmq_watermark, False)
        self.vfo2_to_float = blocks.complex_to_float(1)
        self.vfo2_signal_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (250e3-40e3), mag, 0, 0)
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
        self.vfo2_audio_sink = audio.sink(48000, 'pipewire', False)
        self.vfo0_waterfall_atten = blocks.multiply_const_cc(0.01)
        self.vfo0_waterfall_add = blocks.add_vcc(1)
        self.vfo0_to_float = blocks.complex_to_float(1)
        self.vfo0_spectrum = qtgui.freq_sink_c(
            2048, #size
            window.WIN_HAMMING, #wintype
            40e3, #fc
            24e3, #bw
            '', #name
            2,
            None # parent
        )
        self.vfo0_spectrum.set_update_time(0.01)
        self.vfo0_spectrum.set_y_axis((-94), (-50))
        self.vfo0_spectrum.set_y_label('Relative Gain', 'dB')
        self.vfo0_spectrum.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.vfo0_spectrum.enable_autoscale(False)
        self.vfo0_spectrum.enable_grid(True)
        self.vfo0_spectrum.set_fft_average(0.2)
        self.vfo0_spectrum.enable_axis_labels(True)
        self.vfo0_spectrum.enable_control_panel(False)
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

        for i in range(2):
            if len(labels[i]) == 0:
                self.vfo0_spectrum.set_line_label(i, "Data {0}".format(i))
            else:
                self.vfo0_spectrum.set_line_label(i, labels[i])
            self.vfo0_spectrum.set_line_width(i, widths[i])
            self.vfo0_spectrum.set_line_color(i, colors[i])
            self.vfo0_spectrum.set_line_alpha(i, alphas[i])

        self._vfo0_spectrum_win = sip.wrapinstance(self.vfo0_spectrum.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._vfo0_spectrum_win, 15, 0, 14, 6)
        for r in range(15, 29):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.vfo0_signal_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (250e3-vfo), mag, 0, 0)
        self.vfo0_scope_bandpass = filter.fir_filter_ccc(
            (2*decim),
            firdes.complex_band_pass(
                1,
                samp_rate,
                (-12e3),
                12e3,
                1000,
                window.WIN_HAMMING,
                6.76))
        self.vfo0_mixer = blocks.multiply_vcc(1)
        self.vfo0_bandpass = filter.fir_filter_ccc(
            decim,
            firdes.complex_band_pass(
                20,
                samp_rate,
                rx0_low_cutoff,
                rx0_high_cutoff,
                100,
                window.WIN_HAMMING,
                6.76))
        self.vfo0_audio_sink = audio.sink(48000, '', False)
        self.tx_vfo_signal_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, (tx_vfo - 250e3), mag, 0, 0)
        self.tx_to_complex = blocks.float_to_complex(1)
        self.tx_power_to_msg = blocks.var_to_msg_pair('value')
        self.tx_mixer = blocks.multiply_vcc(1)
        self.tx_bandpass = filter.interp_fir_filter_ccc(
            1,
            firdes.complex_band_pass(
                tx_power,
                48e3,
                0,
                3000,
                200,
                window.WIN_HAMMING,
                6.76))
        self.tx_audio_source = audio.source(48000, '', False)
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

        self.rx_waterfall.set_intensity_range(-80, -50)

        self._rx_waterfall_win = sip.wrapinstance(self.rx_waterfall.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._rx_waterfall_win, 0, 0, 14, 6)
        for r in range(0, 14):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.rx_resampler = filter.rational_resampler_ccc(
                interpolation=decim,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.rx0_low_cutoff_to_msg = blocks.var_to_msg_pair('value')
        self.rx0_high_cutoff_to_msg = blocks.var_to_msg_pair('value')
        self.rational_resampler_4 = filter.rational_resampler_fff(
                interpolation=1,
                decimation=4,
                taps=[],
                fractional_bw=0)
        if "int" == "int":
        	isFloat = False
        else:
        	isFloat = True

        _qtgui_dialgauge_4_lg_win = qtgui.GrDialGauge('Filter BW',"blue","white","black",0,3000, 80, 1,isFloat,True,True,self)
        _qtgui_dialgauge_4_lg_win.setValue(3000)
        self.qtgui_dialgauge_4 = _qtgui_dialgauge_4_lg_win

        self.top_grid_layout.addWidget(_qtgui_dialgauge_4_lg_win, 39, 2, 1, 1)
        for r in range(39, 40):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        if "int" == "int":
        	isFloat = False
        else:
        	isFloat = True

        _qtgui_dialgauge_3_lg_win = qtgui.GrDialGauge('Filter Center',"blue","white","black",0,3000, 80, 1,isFloat,True,True,self)
        _qtgui_dialgauge_3_lg_win.setValue(1500)
        self.qtgui_dialgauge_3 = _qtgui_dialgauge_3_lg_win

        self.top_grid_layout.addWidget(_qtgui_dialgauge_3_lg_win, 39, 1, 1, 1)
        for r in range(39, 40):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        if "real" == "int":
        	isFloat = False
        else:
        	isFloat = True

        _qtgui_dialgauge_2_lg_win = qtgui.GrDialGauge('AF Gain',"blue","white","black",0.0,1.5, 80, 1,isFloat,True,True,self)
        _qtgui_dialgauge_2_lg_win.setValue(1.0)
        self.qtgui_dialgauge_2 = _qtgui_dialgauge_2_lg_win

        self.top_grid_layout.addWidget(_qtgui_dialgauge_2_lg_win, 39, 3, 1, 1)
        for r in range(39, 40):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        if "real" == "int":
        	isFloat = False
        else:
        	isFloat = True

        _qtgui_dialgauge_1_lg_win = qtgui.GrDialGauge('TX Power',"blue","white","black",0.0,1.0, 80, 1,isFloat,True,True,self)
        _qtgui_dialgauge_1_lg_win.setValue(0.1)
        self.qtgui_dialgauge_1 = _qtgui_dialgauge_1_lg_win

        self.top_grid_layout.addWidget(_qtgui_dialgauge_1_lg_win, 39, 4, 1, 1)
        for r in range(39, 40):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(4, 5):
            self.top_grid_layout.setColumnStretch(c, 1)
        if "int" == "int":
        	isFloat = False
        else:
        	isFloat = True

        _qtgui_dialgauge_0_lg_win = qtgui.GrDialGauge('WPM',"blue","white","black",0,56, 80, 1,isFloat,True,True,self)
        _qtgui_dialgauge_0_lg_win.setValue(24)
        self.qtgui_dialgauge_0 = _qtgui_dialgauge_0_lg_win

        self.top_grid_layout.addWidget(_qtgui_dialgauge_0_lg_win, 39, 5, 1, 1)
        for r in range(39, 40):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(5, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
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

        self.top_grid_layout.addWidget(_low_cutoff_gauge_lg_win, 40, 1, 1, 5)
        for r in range(40, 41):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        if "int" == "int":
        	isFloat = False
        	scaleFactor = 1
        else:
        	isFloat = True
        	scaleFactor = 1

        _high_cutoff_gauge_lg_win = qtgui.GrLevelGauge('',"default","default","default",0,3000, 100, False,1,isFloat,scaleFactor,True,self)
        _high_cutoff_gauge_lg_win.setValue(3000)
        self.high_cutoff_gauge = _high_cutoff_gauge_lg_win

        self.top_grid_layout.addWidget(_high_cutoff_gauge_lg_win, 41, 1, 1, 5)
        for r in range(41, 42):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 6):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.ft8_sink = blocks.wavfile_sink(
            '/dev/null',
            1,
            12000,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.ft84_rotate = ft84_rotate.blk(tmp_path='/run/user/1000/gnuradio')
        self.ft84_cron = ft84_cron.blk()
        self.ft4_sink = blocks.wavfile_sink(
            '/dev/null',
            1,
            12000,
            blocks.FORMAT_WAV,
            blocks.FORMAT_PCM_16,
            False
            )
        self.control = control.blk()
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, 24e3, True, 0 if "auto" == "auto" else max( int(float(0.1) * 24e3) if "auto" == "time" else int(0.1), 1) )
        self.blocks_swapiq_0 = blocks.swap_iq(1, gr.sizeof_gr_complex)
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.analog_sig_source_x_0_0 = analog.sig_source_c(24e3, analog.GR_COS_WAVE, rx0_high_cutoff, (1e-3), 0, 0)
        self.analog_sig_source_x_0 = analog.sig_source_c(24e3, analog.GR_COS_WAVE, rx0_low_cutoff, (1e-3), 0, 0)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.control, 'midi_out'), (self.midi_block, 'midi_in'))
        self.msg_connect((self.control, 'wpm_out'), (self.qtgui_dialgauge_0, 'value'))
        self.msg_connect((self.control, 'af_gain_out'), (self.qtgui_dialgauge_2, 'value'))
        self.msg_connect((self.control, 'filter_center_out'), (self.qtgui_dialgauge_3, 'value'))
        self.msg_connect((self.control, 'filter_bw_out'), (self.qtgui_dialgauge_4, 'value'))
        self.msg_connect((self.control, 'tx_freq_out'), (self.tx_vfo, 'valuein'))
        self.msg_connect((self.control, 'rx_freq_out'), (self.vfo, 'valuein'))
        self.msg_connect((self.ft84_cron, 'cron_ft8'), (self.ft84_rotate, 'rotate_ft8'))
        self.msg_connect((self.ft84_cron, 'cron_ft4'), (self.ft84_rotate, 'rotate_ft4'))
        self.msg_connect((self.midi_block, 'midi_out'), (self.control, 'midi_in'))
        self.msg_connect((self.rx0_high_cutoff_to_msg, 'msgout'), (self.high_cutoff_gauge, 'value'))
        self.msg_connect((self.rx0_low_cutoff_to_msg, 'msgout'), (self.low_cutoff_gauge, 'value'))
        self.msg_connect((self.rx_waterfall, 'freq'), (self.vfo, 'valuein'))
        self.msg_connect((self.tx_power_to_msg, 'msgout'), (self.qtgui_dialgauge_1, 'value'))
        self.msg_connect((self.tx_vfo, 'valueout'), (self.control, 'tx_freq_in'))
        self.msg_connect((self.vfo, 'valueout'), (self.control, 'rx_freq_in'))
        self.msg_connect((self.vfo, 'valueout'), (self.vfo0_spectrum, 'freq'))
        self.msg_connect((self.vfo0_spectrum, 'freq'), (self.vfo, 'valuein'))
        self.msg_connect((self.vfo0_spectrum, 'freq'), (self.vfo0_spectrum, 'freq'))
        self.connect((self.analog_sig_source_x_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.analog_sig_source_x_0_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.blocks_swapiq_0, 0), (self.vfo0_waterfall_atten, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.vfo0_spectrum, 1))
        self.connect((self.rational_resampler_4, 0), (self.ft4_sink, 0))
        self.connect((self.rational_resampler_4, 0), (self.ft8_sink, 0))
        self.connect((self.rx_resampler, 0), (self.tx_mixer, 0))
        self.connect((self.tx_audio_source, 0), (self.tx_to_complex, 0))
        self.connect((self.tx_bandpass, 0), (self.rx_resampler, 0))
        self.connect((self.tx_mixer, 0), (self.zeromq_push_sink_0, 0))
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
        self.connect((self.vfo2_to_float, 0), (self.rational_resampler_4, 0))
        self.connect((self.vfo2_to_float, 0), (self.vfo2_audio_sink, 0))
        self.connect((self.zeromq_pull_source_0, 0), (self.vfo0_mixer, 0))
        self.connect((self.zeromq_pull_source_0, 0), (self.vfo0_waterfall_add, 0))
        self.connect((self.zeromq_pull_source_0, 0), (self.vfo2_mixer, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "qo100_local")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_decim(self):
        return self.decim

    def set_decim(self, decim):
        self.decim = decim
        self.set_samp_rate(self.decim*48e3)

    def get_zmq_watermark(self):
        return self.zmq_watermark

    def set_zmq_watermark(self, zmq_watermark):
        self.zmq_watermark = zmq_watermark

    def get_vfo(self):
        return self.vfo

    def set_vfo(self, vfo):
        self.vfo = vfo
        self.vfo0_signal_source.set_frequency((250e3-self.vfo))

    def get_tx_vfo(self):
        return self.tx_vfo

    def set_tx_vfo(self, tx_vfo):
        self.tx_vfo = tx_vfo
        self.tx_vfo_signal_source.set_frequency((self.tx_vfo - 250e3))

    def get_tx_power(self):
        return self.tx_power

    def set_tx_power(self, tx_power):
        self.tx_power = tx_power
        self.tx_bandpass.set_taps(firdes.complex_band_pass(self.tx_power, 48e3, 0, 3000, 200, window.WIN_HAMMING, 6.76))
        self.tx_power_to_msg.variable_changed(self.tx_power)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.rx_waterfall.set_frequency_range(250e3, self.samp_rate)
        self.tx_vfo_signal_source.set_sampling_freq(self.samp_rate)
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(20, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 100, window.WIN_HAMMING, 6.76))
        self.vfo0_scope_bandpass.set_taps(firdes.complex_band_pass(1, self.samp_rate, (-12e3), 12e3, 1000, window.WIN_HAMMING, 6.76))
        self.vfo0_signal_source.set_sampling_freq(self.samp_rate)
        self.vfo2_bandpass.set_taps(firdes.complex_band_pass(10, self.samp_rate, 0, 5000, 1000, window.WIN_HAMMING, 6.76))
        self.vfo2_signal_source.set_sampling_freq(self.samp_rate)

    def get_rx0_low_cutoff(self):
        return self.rx0_low_cutoff

    def set_rx0_low_cutoff(self, rx0_low_cutoff):
        self.rx0_low_cutoff = rx0_low_cutoff
        self.analog_sig_source_x_0.set_frequency(self.rx0_low_cutoff)
        self.rx0_low_cutoff_to_msg.variable_changed(self.rx0_low_cutoff)
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(20, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 100, window.WIN_HAMMING, 6.76))

    def get_rx0_high_cutoff(self):
        return self.rx0_high_cutoff

    def set_rx0_high_cutoff(self, rx0_high_cutoff):
        self.rx0_high_cutoff = rx0_high_cutoff
        self.analog_sig_source_x_0_0.set_frequency(self.rx0_high_cutoff)
        self.rx0_high_cutoff_to_msg.variable_changed(self.rx0_high_cutoff)
        self.vfo0_bandpass.set_taps(firdes.complex_band_pass(20, self.samp_rate, self.rx0_low_cutoff, self.rx0_high_cutoff, 100, window.WIN_HAMMING, 6.76))

    def get_qtgui_dialgauge_4(self):
        return self.qtgui_dialgauge_4

    def set_qtgui_dialgauge_4(self, qtgui_dialgauge_4):
        self.qtgui_dialgauge_4 = qtgui_dialgauge_4
        self.qtgui_dialgauge_4.setValue(3000)

    def get_qtgui_dialgauge_3(self):
        return self.qtgui_dialgauge_3

    def set_qtgui_dialgauge_3(self, qtgui_dialgauge_3):
        self.qtgui_dialgauge_3 = qtgui_dialgauge_3
        self.qtgui_dialgauge_3.setValue(1500)

    def get_qtgui_dialgauge_2(self):
        return self.qtgui_dialgauge_2

    def set_qtgui_dialgauge_2(self, qtgui_dialgauge_2):
        self.qtgui_dialgauge_2 = qtgui_dialgauge_2
        self.qtgui_dialgauge_2.setValue(1.0)

    def get_qtgui_dialgauge_1(self):
        return self.qtgui_dialgauge_1

    def set_qtgui_dialgauge_1(self, qtgui_dialgauge_1):
        self.qtgui_dialgauge_1 = qtgui_dialgauge_1
        self.qtgui_dialgauge_1.setValue(0.1)

    def get_qtgui_dialgauge_0(self):
        return self.qtgui_dialgauge_0

    def set_qtgui_dialgauge_0(self, qtgui_dialgauge_0):
        self.qtgui_dialgauge_0 = qtgui_dialgauge_0
        self.qtgui_dialgauge_0.setValue(24)

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




def main(top_block_cls=qo100_local, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()
    snippets_main_after_init(tb)
    tb.start()
    tb.flowgraph_started.set()

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

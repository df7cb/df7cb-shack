## Requirements

apt-get install \
 gnuradio \
 gr-limesdr \
 python3-matplotlib \
 python3-mido \
 python3-pulsectl \
 python3-rtmidi \
 soapysdr-module-lms7 \
 wsjtx

LimeUtil --refclk

https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/Virtual-Devices

# https://www.dm5wk.de/notes/posts/2024-0001-audio_devices_for_amateur_radio/
pactl load-module module-null-sink media.class=Audio/Sink sink_name=tx0
pactl load-module module-null-sink media.class=Audio/Sink sink_name=rx2

context.objects = [
    {   factory = adapter
        args = {
           factory.name     = support.null-audio-sink
           node.name        = "my-sink"
           media.class      = Audio/Sink
           object.linger    = true
           audio.position   = [ FL FR FC LFE RL RR ]
           monitor.channel-volumes = true
           monitor.passthrough = true
        }
    }
]

sudo uhubctl -l 1-1 -a 0

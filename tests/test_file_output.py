import time, pytest, inspect
from utils import *
from PIL import Image

def test_can_create_video_file_output(run_brave, create_config_file):
    output_video_location = create_output_video_location()

    config = {
    'inputs': [
        {'type': 'test_video', 'pattern': 4}, # pattern 4 is red
    ],
    'outputs': [
        {'type': 'file',  'location': output_video_location } 
        # ,{'type': 'local'} # good for debugging
    ]
    }
    config_file = create_config_file(config)
    run_brave(config_file.name)
    time.sleep(4)
    check_brave_is_running()
    response = api_get('/api/all')
    assert response.status_code == 200
    assert_everything_in_playing_state(response.json())
    assert os.path.exists(output_video_location)


def test_valid_output_file():
    assert_valid_output_file(get_output_video_location())


def stop_output(num):
    path = '/api/outputs/%d' % num
    response = api_post(path, {'state': 'READY'})
    assert response.status_code == 200, 'Status code for %s was %d' % (path, response.status_code)

def assert_valid_output_file(output_video_location):
    '''
    Given a file, validates it is a video (mp4) file
    '''
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib

    Gst.init(None)

    # We create a pipeline so that we can read the file and check it:
    pipeline = Gst.ElementFactory.make("playbin")
    pipeline.set_property('uri','file://'+output_video_location)
    playsink = pipeline.get_by_name('playsink')
    playsink.set_property('video-sink', Gst.ElementFactory.make('fakesink'))
    ret = pipeline.set_state(Gst.State.PAUSED)

    assert ret != Gst.StateChangeReturn.FAILURE

    bus = pipeline.get_bus()

    while True:
        message = bus.timed_pop_filtered(
            Gst.CLOCK_TIME_NONE,
            Gst.MessageType.STATE_CHANGED |
            Gst.MessageType.ERROR |
            Gst.MessageType.EOS
        )
        assert message.type != Gst.MessageType.ERROR
        if message.type == Gst.MessageType.EOS:
            break
        assert message.type == Gst.MessageType.STATE_CHANGED
        if message.src == pipeline:
            old_state, new_state, pending_state = message.parse_state_changed()
            if new_state == Gst.State.PAUSED:
                element = pipeline.get_by_name('inputselector1')
                caps = element.get_static_pad('src').get_current_caps().to_string()
                assert caps == 'audio/x-raw, format=(string)F32LE, layout=(string)non-interleaved,' \
                               ' rate=(int)48000, channels=(int)2, channel-mask=(bitmask)0x0000000000000003'

                element = pipeline.get_by_name('inputselector0')
                caps = element.get_static_pad('src').get_current_caps().to_string()
                assert caps == 'video/x-raw,' \
                               ' format=(string)NV12,' \
                               ' width=(int)640,' \
                               ' height=(int)360,' \
                               ' interlace-mode=(string)progressive,' \
                               ' multiview-mode=(string)mono,' \
                               ' multiview-flags=(GstVideoMultiviewFlagsSet)0:ffffffff:/right-view-first/left-flipped/left-flopped/right-flipped/right-flopped/half-aspect/mixed-mono,' \
                               ' pixel-aspect-ratio=(fraction)1/1,' \
                               ' chroma-site=(string)jpeg,' \
                               ' colorimetry=(string)bt601,' \
                               ' framerate=(fraction)30/1'
                break

    pipeline.set_state(Gst.State.NULL)

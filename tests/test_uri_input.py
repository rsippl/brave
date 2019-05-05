import time, pytest
from utils import *
FIVE_SECOND_VIDEO = 'file://' + assets_directory() + '/5_second_video.mp4'
# TWO_SECOND_VIDEO = 'file://' + assets_directory() + '/2_second_video.mp4'


def test_uri_input_from_command_line(run_brave, create_config_file):
    config = {
        'inputs': [
            {'type': 'uri', 'uri': FIVE_SECOND_VIDEO},
        ]
   }

    response_json = run_brave_and_get_all_response(run_brave, create_config_file(config))
    assert_everything_in_playing_state(response_json)
    assert len(response_json['inputs']) == 1
    assert response_json['inputs'][0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json['inputs'][0]['loop'] == False
    assert response_json['inputs'][0]['state'] == 'PLAYING'

    subtest_check_deleted_input_goes_away()


def test_loop(run_brave, create_config_file):
    config = {
        'inputs': [
            {'type': 'uri', 'uri': FIVE_SECOND_VIDEO},
            {'type': 'uri', 'uri': FIVE_SECOND_VIDEO, 'loop': True},
        ]
   }

    response_json = run_brave_and_get_all_response(run_brave, create_config_file(config))
    time.sleep(0.5)
    assert_everything_in_playing_state(response_json)
    assert len(response_json['inputs']) == 2
    assert response_json['inputs'][0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json['inputs'][0]['loop'] == False
    assert response_json['inputs'][0]['state'] == 'PLAYING'
    assert response_json['inputs'][1]['uri'] == FIVE_SECOND_VIDEO
    assert response_json['inputs'][1]['loop'] == True
    assert response_json['inputs'][1]['state'] == 'PLAYING'

    time.sleep(5)
    response = api_get('/api/all')
    response_json = response.json()
    assert len(response_json['inputs']) == 2
    assert response_json['inputs'][0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json['inputs'][0]['loop'] == False
    assert response_json['inputs'][0]['state'] == 'READY'
    assert response_json['inputs'][1]['uri'] == FIVE_SECOND_VIDEO
    assert response_json['inputs'][1]['loop'] == True
    assert response_json['inputs'][1]['state'] == 'PLAYING'


def test_uri_position_seeking(run_brave, create_config_file):

    # We create a new input that should start be at 2000000000 (2 seconds):
    config = {
        'inputs': [
            {'type': 'uri', 'uri': FIVE_SECOND_VIDEO, 'position': 2000000000, 'state': 'READY'}
        ]
   }

    response_json = run_brave_and_get_all_response(run_brave, create_config_file(config))
    print('response_json=', response_json)
    assert len(response_json['inputs']) == 1
    assert response_json['inputs'][0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json['inputs'][0]['state'] == 'READY'
    assert response_json['inputs'][0]['position'] == 2000000000

    # Set to PAUSED and check the position remains
    update_input(1, {'state': 'PAUSED'})
    time.sleep(1)
    response = api_get('/api/inputs')
    assert response.status_code == 200
    response_json = response.json()

    print('response_json=', response_json)
    assert len(response_json) == 1
    assert response_json[0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json[0]['state'] == 'PAUSED'
    assert response_json[0]['position'] == 2000000000
    # assert response_json[0]['position'] > 3000000000

    # Now change the position to 500000000 (0.5 seconds)
    update_input(1, {'position': 500000000})
    time.sleep(0.5)
    response = api_get('/api/inputs')
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 1
    assert response_json[0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json[0]['state'] == 'PAUSED'
    assert response_json[0]['position'] == 500000000

    # Now start playing... it should increase
    update_input(1, {'state': 'PLAYING'})
    time.sleep(1)
    response = api_get('/api/inputs')
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json) == 1
    assert response_json[0]['uri'] == FIVE_SECOND_VIDEO
    assert response_json[0]['state'] == 'PLAYING'

    # Allow somethign bigger than 0.5 seconds and 2 seconds (as we slept for 1 second)
    assert 500000000 < response_json[0]['position'] < 2000000000


def test_missing_file_input_from_command_line(run_brave, create_config_file):
    uri = 'file:///does-not-exist'
    config = {
        'inputs': [
            {'type': 'uri', 'uri': uri},
        ]
    }

    response_json = run_brave_and_get_all_response(run_brave, create_config_file(config))
    time.sleep(0.5)

    # Expect NULL state for the input, otherwise everything is PLAYING
    assert_outputs_in_playing_state(response_json)
    assert_mixers_in_playing_state(response_json)
    assert len(response_json['inputs']) == 1
    assert response_json['inputs'][0]['state'] == 'NULL'
    subtest_check_deleted_input_goes_away()


def test_uri_input_from_api(run_brave):
    run_brave()
    check_brave_is_running()
    add_input({'type': 'uri', 'uri': FIVE_SECOND_VIDEO})

    # Immediately goes into READY state, pending a move to PLAYING
    response = api_get('/api/inputs')
    assert len(response.json()) == 1
    assert response.json()[0]['state'] == 'READY'
    assert response.json()[0]['desired_state'] == 'PLAYING'

    # After a second, should have moved into PLAYING state
    time.sleep(1)
    response = api_get('/api/inputs')
    assert len(response.json()) == 1
    assert response.json()[0]['state'] == 'PLAYING'
    assert 'desired_state' not in response.json()[0]


def subtest_check_deleted_input_goes_away():
    # Now delete the input, it should go away
    delete_input(1)
    time.sleep(1)
    response = api_get('/api/all')
    assert response.status_code == 200
    response_json = response.json()

    assert len(response_json['inputs']) == 0
    assert_everything_in_playing_state(response_json)


def run_brave_and_get_all_response(run_brave, config_file):
    run_brave(config_file.name)
    time.sleep(0.5)
    check_brave_is_running()
    time.sleep(1.5)
    response = api_get('/api/all')
    assert response.status_code == 200
    return response.json()

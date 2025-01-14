#!/usr/bin/python3
import argparse
import json
import os
import sys
import subprocess
import tempfile
import time
import threading
import logging


def get_parameters(run_command):
    uid = os.getuid()
    gid = os.getgid()

    app_username = os.getenv("APP_USERNAME", "")
    app_password = os.getenv("APP_PASSWORD", "")

    logging.debug("%s: APP_USERNAME %s" % (args.keyword, app_username))
    logging.debug("%s: APP_PASSWORD %s" % (args.keyword, app_password))

    # Loading storage server version name
    if run_command == 'run_backfill.py':
        file_location = '../../storage/version.txt'
        f = open(file_location, 'r')
    else:
        try:
            file_location = '../../storage/version.txt'
            f = open(file_location, 'r')
        except:
            file_location = '../../storage/version.txt'
            f = open(file_location, 'r')

    version = f.read()
    version = version.strip('\n')

    # Getting current user
    process = subprocess.Popen(
        ['whoami'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    developer = stdout.decode('utf-8')[:-1]

    return uid, gid, app_username, app_password, version, developer


def kill_all_containers():
    logging.debug('killing all containers')

    process = subprocess.Popen(['docker', 'container', 'kill'] + containers,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    lock.acquire()
    killed_container_ids = stdout.decode('utf-8').split()
    for c in killed_container_ids:
        logging.debug('killed container {0}'.format(c))
    logging.debug(stderr)
    logging.debug("\n")
    lock.release()


def wait_container(container):
    process = subprocess.Popen([
        'docker', 'container', 'wait',
        container],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    process = subprocess.Popen([
        'docker', 'inspect', container, "--format='{{.State.ExitCode}}'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    status = stdout.decode('utf-8')

    ## logging.debug is not thread-safe
    # acquire a lock
    lock.acquire()
    logging.debug("%s: %s exited with status code %s" % (args.keyword, container_dict[container], status))
    # remove the container from global list and dict
    # in a thread-safe way
    containers.remove(container)
    del container_dict[container]
    # release lock
    lock.release()


lock = threading.Lock()
# a global list of container id's
containers = []
container_dict = {}

if __name__ == '__main__':
    logging.basicConfig(filename='run_backfill.log', level=logging.DEBUG)
    logging.debug("run_backfill.py")

    parser = argparse.ArgumentParser(description='EduSense deploy video')
    parser.add_argument('--front_video', dest='front_video', type=str, nargs='?',
                        required=True, help='video file for front ip camera')
    parser.add_argument('--developer', dest='dev', type=str, nargs='?',
                        required=True, help='enter developer tag name')
    parser.add_argument('--back_video', dest='back_video', type=str, nargs='?',
                        required=True, help='video for back ip camera')
    parser.add_argument('--keyword', dest='keyword', type=str, nargs='?',
                        required=True, help='Keyword for class session')
    parser.add_argument('--backend_url', dest='backend_url', type=str, nargs='?',
                        required=True, help='EduSense backend address')
    parser.add_argument('--front_num_gpu_start', dest='front_num_gpu_start', type=int, nargs='?',
                        required=True, help='GPU start index for front camera processing')
    parser.add_argument('--front_num_gpu', dest='front_num_gpu', type=int, nargs='?',
                        required=True, help='number of GPUs for front camera processing')
    parser.add_argument('--back_num_gpu_start', dest='back_num_gpu_start', type=int, nargs='?',
                        required=True, help='GPU start index for back camera processing')
    parser.add_argument('--back_num_gpu', dest='back_num_gpu', type=int, nargs='?',
                        required=True, help='number of GPUs for back camera processing')
    parser.add_argument('--time_duration', dest='time_duration', type=int, nargs='?',
                        required=True, help='time duration for executing CI')
    parser.add_argument('--video_schema', dest='video_schema', type=str, nargs='?',
                        required=True, help='video schema for CI')
    parser.add_argument('--audio_schema', dest='audio_schema', type=str, nargs='?',
                        required=True, help='audio schema for CI')
    parser.add_argument('--timeout', dest='timeout', type=int, nargs='?',
                        help='timeout for the script', default=72000)
    parser.add_argument('--log_dir', dest='log_dir', type=str, nargs='?',
                        help='get the logs in a directory')
    parser.add_argument('--video_dir', dest='video_dir', type=str, nargs='?',
                        required=True, help='directory for video')
    parser.add_argument('--process_real_time', dest='process_real_time',
                        action='store_true', help='if set, skip frames to keep'
                                                  ' realtime')
    parser.add_argument('--tensorflow_gpu', dest='tensorflow_gpu', type=str, nargs='?',
                        default='-1', help='tensorflow gpus')
    parser.add_argument('--overwrite', dest='overwrite', type=str, nargs='?', default='False',
                        help='To enable overwriting previous backfilled session, enter: True')
    parser.add_argument('--backfillFPS', dest='backfillFPS', type=str, nargs='?',
                        required=False, help='FPS for backfill', default=0)
    args = parser.parse_args()

    uid, gid, app_username, app_password, version, developer = get_parameters(
        sys.argv[0])

    # curl_comm = [
    #     'curl',
    #     '-X', 'POST',
    #     '-d', '{\"developer\": \"%s\", \"version\": \"%s\", \"keyword\": \"%s\", \"overwrite\": \"%s\"}' % (
    #         developer, version, args.keyword, args.overwrite),
    #     '--header', 'Content-Type: application/json',
    #     '--basic', '-u', '%s:%s' % (app_username, app_password),
    #     'https://%s/sessions' % args.backend_url]

    # logging.debug(curl_comm)

    # Calling sessions API endpoint
    process = subprocess.Popen([
        'curl',
        '-X', 'POST',
        '-d', '{\"developer\": \"%s\", \"version\": \"%s\", \"keyword\": \"%s\", \"overwrite\": \"%s\"}' % (
            developer, version, args.keyword, args.overwrite),
        '--header', 'Content-Type: application/json',
        '--basic', '-u', '%s:%s' % (app_username, app_password),
              'https://%s/sessions' % args.backend_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    logging.debug("%s: stdout from session" % (args.keyword))
    logging.debug(stdout)
    logging.debug("%s: stderr from session" % (args.keyword))
    logging.debug(stderr)

    try:
        output = json.loads(stdout.decode('utf-8'))
        success = output['success']
        session_id = output['session_id'].strip()

    except:
        logging.debug("Unable to create a session")
        logging.debug("check APP username and password")
        sys.exit(1)

    logging.debug('%s: created session %s' % (args.keyword, session_id))

    real_time_flag = ['--process_real_time'] if args.process_real_time \
        else []

    vid_comm = [
                   'docker', 'run', '-d',
                   '--gpus', 'device=%d' % (args.front_num_gpu_start),
                   '-e', 'LOCAL_USER_ID=%s' % uid,
                   '-e', 'APP_USERNAME=%s' % app_username,
                   '-e', 'APP_PASSWORD=%s' % app_password,
                   '-v', '%s:/app/source' % args.video_dir,
                   '-v', '%s:/tmp' % args.log_dir,
                         'edusense/video:' + args.dev,
                   '--video', os.path.join('/app', 'source', args.front_video),
                   '--video_sock', '/tmp/unix.front.sock',
                   '--backend_url', args.backend_url,
                   '--session_id', session_id,
                   '--schema', args.video_schema,
                   '--use_unix_socket',
                   '--keep_frame_number',
                   '--backfillFPS', args.backfillFPS,
                   '--process_gaze',
                   '--time_duration',
                   str(args.time_duration + 60) if args.time_duration >= 0 else '-1'] + real_time_flag
    logging.debug(vid_comm)

    # create temp directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        if args.log_dir == None:
            args.log_dir = tmp_dir
            logging.debug('%s: create temporary directory %s' % (args.keyword, tmp_dir))
        process = subprocess.Popen([
                                       'docker', 'run', '-d',
                                       '--gpus', 'device=%d' % (args.front_num_gpu_start),
                                       '-e', 'LOCAL_USER_ID=%s' % uid,
                                       '-e', 'APP_USERNAME=%s' % app_username,
                                       '-e', 'APP_PASSWORD=%s' % app_password,
                                       '-v', '%s:/app/source' % args.video_dir,
                                       '-v', '%s:/tmp' % args.log_dir,
                                                 'edusense/video:' + args.dev,
                                       '--video', os.path.join('/app', 'source', args.front_video),
                                       '--video_sock', '/tmp/unix.front.sock',
                                       '--backend_url', args.backend_url,
                                       '--session_id', session_id,
                                       '--schema', args.video_schema,
                                       '--use_unix_socket',
                                       '--keep_frame_number',
                                       '--backfillFPS', args.backfillFPS,
                                       '--gaze_3d',
                                       '--time_duration',
                                       str(args.time_duration + 60) if args.time_duration >= 0 else '-1'] + real_time_flag,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.debug("%s: Output of front video container:" % (args.keyword))
        logging.debug(stdout)
        logging.debug("%s: Error of front video container:" % (args.keyword))
        logging.debug(stderr)
        front_video_container_id = stdout.decode('utf-8').strip()
        containers.append(front_video_container_id)
        container_dict[front_video_container_id] = 'front video container'
        logging.debug('%s: created front video container %s' %
                      (args.keyword, front_video_container_id))

        process = subprocess.Popen([
                                       'docker', 'run', '-d',
                                       '--gpus', 'device=%d' % (args.back_num_gpu_start),
                                       '-e', 'LOCAL_USER_ID=%s' % uid,
                                       '-e', 'APP_USERNAME=%s' % app_username,
                                       '-e', 'APP_PASSWORD=%s' % app_password,
                                       '-v', '%s:/tmp' % args.log_dir,
                                       '-v', '%s:/app/source' % args.video_dir,
                                                 'edusense/video:' + args.dev,
                                       '--video', os.path.join('/app', 'source', args.back_video),
                                       '--video_sock', '/tmp/unix.back.sock',
                                       '--backend_url', args.backend_url,
                                       '--session_id', session_id,
                                       '--schema', args.video_schema,
                                       '--gaze_3d',
                                       '--use_unix_socket',
                                       '--backfillFPS', args.backfillFPS,
                                       '--keep_frame_number',
                                       '--time_duration', str(args.time_duration +
                                                              60) if args.time_duration >= 0 else '-1',
                                       '--instructor'] + real_time_flag,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.debug("%s: Output of back video container:" % (args.keyword))
        logging.debug(stdout)
        logging.debug("%s: Error of back video container:" % (args.keyword))
        logging.debug(stderr)
        back_video_container_id = stdout.decode('utf-8').strip()
        containers.append(back_video_container_id)
        container_dict[back_video_container_id] = 'back video container'
        logging.debug('%s: created back video container %s' %
                      (args.keyword, back_video_container_id))

        time.sleep(30)

        process = subprocess.Popen([
                                       'nvidia-docker', 'run', '-d',
                                       '-e', 'LOCAL_USER_ID=%s' % uid,
                                       '-v', '%s:/tmp' % args.log_dir,
                                       '-v', '%s:/app/video' % args.video_dir,
                                             'edusense/openpose:' + args.dev,
                                       '--video', os.path.join('/app', 'video', args.front_video),
                                       '--num_gpu_start', str(args.front_num_gpu_start),
                                       '--num_gpu', str(args.front_num_gpu),
                                       '--use_unix_socket',
                                       '--unix_socket', os.path.join('/tmp', 'unix.front.sock'),
                                       '--display', '0',
                                       '--render_pose', '0',
                                       '--raw_image'] + real_time_flag,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.debug("%s: Output of front openpose container:" % (args.keyword))
        logging.debug(stdout)
        logging.debug("%s: Error of front openpose container:" % (args.keyword))
        logging.debug(stderr)
        front_openpose_container_id = stdout.decode('utf-8').strip()
        containers.append(front_openpose_container_id)
        container_dict[front_openpose_container_id] = 'front openpose container'
        logging.debug('%s: created front openpose container %s' %
                      (args.keyword, front_openpose_container_id))

        process = subprocess.Popen([
                                       'nvidia-docker', 'run', '-d',
                                       '-e', 'LOCAL_USER_ID=%s' % uid,
                                       '-v', '%s:/tmp' % args.log_dir,
                                       '-v', '%s:/app/video' % args.video_dir,
                                             'edusense/openpose:' + args.dev,
                                       '--video', os.path.join('/app', 'video', args.back_video),
                                       '--num_gpu_start', str(args.back_num_gpu_start),
                                       '--num_gpu', str(args.back_num_gpu),
                                       '--use_unix_socket',
                                       '--unix_socket', os.path.join('/tmp', 'unix.back.sock'),
                                       '--display', '0',
                                       '--render_pose', '0',
                                       '--raw_image'] + real_time_flag,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.debug("%s: Output of back openpose container:" % (args.keyword))
        logging.debug(stdout)
        logging.debug("%s: Error of back openpose container:" % (args.keyword))
        logging.debug(stderr)
        back_openpose_container_id = stdout.decode('utf-8').strip()
        containers.append(back_openpose_container_id)
        container_dict[back_openpose_container_id] = 'back openpose container'
        logging.debug('%s: created back openpose container %s' %
                      (args.keyword, back_openpose_container_id))

        process = subprocess.Popen([
            'docker', 'run', '-d',
            '-e', 'LOCAL_USER_ID=%s' % uid,
            '-e', 'APP_USERNAME=%s' % app_username,
            '-e', 'APP_PASSWORD=%s' % app_password,
            '-v', '%s:/app/video' % args.video_dir,
            '-v', '%s:/tmp' % args.log_dir,
                  'edusense/audio:' + args.dev,
            '--front_url', os.path.join('/app', 'video', args.front_video),
            '--back_url', os.path.join('/app', 'video', args.back_video),
            '--backend_url', args.backend_url,
            '--session_id', session_id,
            '--time_duration', str(args.time_duration +
                                   60) if args.time_duration >= 0 else '-1',
            '--schema', args.audio_schema],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        logging.debug("%s: Output of audio container:" % (args.keyword))
        logging.debug(stdout)
        logging.debug("%s: Error of audio container:" % (args.keyword))
        logging.debug(stderr)
        audio_container_id = stdout.decode('utf-8').strip()
        containers.append(audio_container_id)
        container_dict[audio_container_id] = 'audio container'
        logging.debug('%s: created audio container %s \n\n' % (args.keyword, audio_container_id))

        # the script can be kept running and dockers will be killed after timeout seconds
        timer = threading.Timer(args.timeout, kill_all_containers)
        timer.start()

        # make seperate threads for containers
        threads = []
        for container in containers:
            t = threading.Thread(target=wait_container, args=[container])
            t.start()
            threads.append(t)

        # join the threads
        for thread in threads:
            thread.join()

        # cancel the killing thread execution
        timer.cancel()

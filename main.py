# coding=utf-8
from __future__ import unicode_literals
import os.path
import json

import config
import achievements
import audio
import announces
from testlink import dao, report
from testlink import setup as setup_testlink
from datetime import datetime
from bottle import route, run, static_file, hook, request, abort, post

ROOT = os.path.abspath(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(ROOT, "static")

quests = achievements.setup(os.path.join(ROOT, 'messages.yml'))
announcedb = announces.Announces(config.ANNOUNCES_FILE)


@route('/report.<output>')
def generate_report(output):
    test_report = dao.manual_test_report()
    return report.generate_report(test_report, output)


@route('/dashboard.json')
def dashboard():
    dashboard = dao.dashboard()
    return json.dumps(dashboard)


@route('/')
def index():
    return static_file('index.html', root=STATIC_ROOT)


@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=STATIC_ROOT)


@route('/achievements.json')
def list_achievements():
    return find_announces()


@route('/achievements/<timestamp>.wav')
def achievements_audio(timestamp):
    return generate_audio(timestamp)


@route('/announces.json')
def list_announces():
    return find_announces()


@route('/announces/<timestamp>.wav')
def announces_audio(timestamp):
    return generate_audio(timestamp)


@post('/announces/add')
def add_announce():
    for key in ('announcement', 'category'):
        if key not in request.forms:
            abort(400, 'missing parameter: {}'.format(key))

    announce = {'announcement': request.forms['announcement'].decode('utf8'),
                'category': request.forms['category'].decode('utf8')}

    if 'timestamp' in request.forms:
        try:
            datetime.strptime(request.forms['timestamp'], "%Y-%m-%dT%H:%M:%S")
            announce['timestamp'] = request.forms['timestamp']
        except ValueError:
            abort(400, 'invalid timestamp')
    else:
        announce['timestamp'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    announcedb.add(announce)


def find_announces():
    timestamp = request.query.get('timestamp', None)
    for announce in quests.announces():
        announcedb.add(announce)
    announces = announcedb.all()
    if timestamp:
        announces = [a for a in announces if a['timestamp'] > timestamp]
    for announce in announces:
        announce['audio'] = "/achievements/{}.wav".format(announce['timestamp'])
    return json.dumps(announces)


@route('/announces/<timestamp>.wav')
def generate_audio(timestamp):
    achievements = announcedb.all()
    sentences = [a['announcement']
                 for a in achievements
                 if a['timestamp'] == timestamp]

    if not sentences:
        abort(404)

    filename = "{}.wav".format(timestamp)
    audio.generate(filename, sentences)

    return static_file(filename, root=config.AUDIO_DIR)


@hook('before_request')
def refresh_build():
    dao.build.refresh()


def setup():
    setup_testlink(host=config.DB_HOST,
                   port=config.DB_PORT,
                   database=config.DB_NAME,
                   user=config.DB_USER,
                   password=config.DB_PASSWORD,
                   project=config.PROJECT_NAME)


if __name__ == "__main__":
    setup()
    run(host=config.HOST, port=config.PORT, reloader=config.DEBUG_RELOAD)

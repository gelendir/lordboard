# coding=utf-8
import asyncio
import os.path
import json

from aiohttp import web
from datetime import datetime, date, time

from testlink import DaoSession, report

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"

class Lordboard:

    def __init__(self, dao):
        self.dao = dao

    @asyncio.coroutine
    def dashboard(self, request):
        result = yield from self.dao.dashboard()
        return web.Response(body=json.dumps(result).encode())

    @asyncio.coroutine
    def report(self, request):
        output = request.match_info.get('output', 'html')
        report_data = yield from self.dao.manual_test_report()
        generated_report = report.generate_report(report_data)
        return web.Response(body=generated_report.encode())

    @asyncio.coroutine
    def logs(self, request):
        latest = request.GET.get('latest', '1') == '1'
        status = request.GET.get('status')
        sort = request.GET.get('sort', 'timestamp')
        order = request.GET.get('order', 'asc')

        timestamp = None
        if 'timestamp' in request.GET:
            timestamp = datetime.strptime(request.GET['timestamp'], DATETIME_FORMAT)

        logs = yield from self.dao.log_journal(latest, timestamp, status, sort, order)
        for log in logs:
            log['timestamp'] = log['timestamp'].strftime(DATETIME_FORMAT)

        body = json.dumps({'logs': logs})
        return web.Response(body=body.encode())


def register_routes(app, config):
    dao = DaoSession(username=config.DB_USER,
                     password=config.DB_PASSWORD,
                     database=config.DB_NAME,
                     host=config.DB_HOST,
                     project=config.PROJECT_NAME,
                     port=config.DB_PORT)
    lordboard = Lordboard(dao)
    app.router.add_route('GET', '/dashboard', lordboard.dashboard)
    app.router.add_route('GET', '/report.{output:[^{}/?#]+}', lordboard.report)
    app.router.add_route('GET', '/logs', lordboard.logs)

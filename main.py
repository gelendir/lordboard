import asyncio
import logging
import os

from aiohttp import web as aioweb

from lordboard import web
import config

ROOT = os.path.abspath(os.path.dirname(__file__))
STATIC_ROOT = os.path.join(ROOT, "static")

logger = logging.getLogger('lordboard')


@asyncio.coroutine
def log_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        response = yield from handler(request)
        logger.info("%s %d - %s", request.method, response.status, request.path)
        return response
    return middleware


@asyncio.coroutine
def static(request):
    filepath = request.match_info.get('path', 'index.html')
    path = os.path.join(STATIC_ROOT, filepath)
    if os.path.exists(path):
        with open(path, 'rb') as f:
            body = f.read()
            return aioweb.Response(body=body)
    return aioweb.Response(status=404)


def build_app(loop):
    app = aioweb.Application(loop=loop, middlewares=[log_middleware])
    app.router.add_route('GET', '/', static)
    app.router.add_route('GET', '/static/{path:[^?]*}', static)
    web.register_routes(app, config)
    return app


def run_server():
    loop = asyncio.get_event_loop()
    app = build_app(loop)

    handler = app.make_handler()
    server = loop.create_server(handler, config.HOST, config.PORT)
    srv = loop.run_until_complete(server)

    logger.info("Starting server on %s", srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down")
        loop.run_until_complete(handler.finish_connections(1.0))
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(app.finish())
    loop.close()


def main():
    logging.basicConfig(level=logging.INFO)
    run_server()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Central HTTP/WebSocket server. Run independently of the desktop SDK."""
import asyncio
import hashlib
from contextlib import suppress
from pathlib import Path
from dataclasses import dataclass
from aiohttp import web, WSMsgType
from .physics.model import Robot
from .drivers import DRIVERS

ROOT = Path(__file__).resolve().parent
ROBOT = web.AppKey('robot', Robot)


@dataclass
class SdkLink:
    socket: object = None


PEER = web.AppKey('sdk_peer', SdkLink)
DRIVER_CLIENTS = web.AppKey('driver_clients', set)


async def simulator(request):
    if request.app[PEER].socket is not None:
        raise web.HTTPConflict(text='One SDK connection is already active')
    ws = web.WebSocketResponse(heartbeat=1, max_msg_size=1024 * 1024)
    # Claim ownership before yielding so two simultaneous upgrades cannot race.
    request.app[PEER].socket = ws
    robot = request.app[ROBOT]
    try:
        await ws.prepare(request)
        robot.failsafe()
        robot.connected = True
        async for message in ws:
            if message.type == WSMsgType.TEXT:
                try:
                    data = message.json()
                    if not isinstance(data, dict):
                        raise ValueError('Expected object')
                    reply = robot.exchange(data)
                except (ValueError, TypeError) as error:
                    reply = dict(type='lynx', status='error', message=str(error))
                await ws.send_json(reply)
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        robot.failsafe()
        robot.connected = False
        request.app[PEER].socket = None
    return ws


async def state(request):
    return web.json_response(request.app[ROBOT].snapshot(), headers={'Cache-Control': 'no-store'})


async def drivers(request):
    """Live physical state, separate from the SDK-owned control connection."""
    origin = request.headers.get('Origin')
    if origin and origin != f'{request.scheme}://{request.host}':
        raise web.HTTPForbidden(text='Open the Driver Station from the simulator origin')
    ws = web.WebSocketResponse(heartbeat=5, max_msg_size=65536)
    await ws.prepare(request)
    await ws.send_json(dict(type='drivers', drivers=DRIVERS.catalog()))
    robot = request.app[ROBOT]
    request.app[DRIVER_CLIENTS].add(ws)

    async def publish():
        while not ws.closed:
            await ws.send_json(robot.snapshot())
            await asyncio.sleep(.1)

    task = asyncio.create_task(publish())
    try:
        async for message in ws:
            if message.type == WSMsgType.TEXT:
                try:
                    data = message.json()
                    if not isinstance(data, dict) or data.get('type') != 'motion':
                        raise ValueError('Expected motion input')
                    if data.keys() - {'type', 'vx', 'vy', 'angular_velocity'}:
                        raise ValueError('Unknown motion fields')
                    if not robot.connected:
                        raise ValueError('Connect the SDK before applying sensor motion')
                    robot.set_motion(**{k: v for k, v in data.items() if k != 'type'})
                    await ws.send_json(dict(type='ack', message='Sensor motion applied'))
                except (ValueError, TypeError) as error:
                    await ws.send_json(dict(type='error', message=str(error)))
            elif message.type == WSMsgType.ERROR:
                break
    finally:
        request.app[DRIVER_CLIENTS].discard(ws)
        task.cancel()
        with suppress(asyncio.CancelledError, ConnectionError):
            await task
    return ws


async def driver_types(request):
    return web.json_response(DRIVERS.catalog(), headers={'Cache-Control': 'no-store'})


async def ds(request):
    # This route is static: no Driver Station state or SDK proxy exists in Python.
    assets = ROOT / 'ds' / 'assets'
    digest = hashlib.sha256()
    for source in sorted(assets.rglob('*.js')):
        digest.update(str(source.relative_to(assets)).encode())
        digest.update(source.read_bytes())
    version = digest.hexdigest()[:16]
    html = (ROOT / 'ds' / 'index.html').read_text().replace('__FTCSIM_ASSET_VERSION__', version)
    return web.Response(text=html, content_type='text/html', headers={'Cache-Control': 'no-store'})


async def ds_asset(request):
    # Relative ES imports retain the version directory, so changing any module
    # invalidates the entire graph rather than mixing old and new dependencies.
    assets = (ROOT / 'ds' / 'assets').resolve()
    source = (assets / request.match_info['filename']).resolve()
    if not source.is_relative_to(assets) or not source.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(source, headers={'Cache-Control': 'no-store'})


async def home(request):
    raise web.HTTPFound('/ds')


async def lifecycle(app):
    async def tick():
        loop = asyncio.get_running_loop()
        previous = loop.time()
        while True:
            await asyncio.sleep(.02)
            now = loop.time()
            app[ROBOT].advance(min(now - previous, .1))
            previous = now
    task = asyncio.create_task(tick())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    if app[PEER].socket is not None:
        await app[PEER].socket.close(code=1001, message=b'Simulator stopping')
    app[ROBOT].failsafe()
    for ws in list(app[DRIVER_CLIENTS]):
        await ws.close(code=1001, message=b'Simulator stopping')


@web.middleware
async def driver_station_cache(request, handler):
    response = await handler(request)
    if request.path.startswith('/ds/assets/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


def create_app():
    app = web.Application(client_max_size=1024 * 1024, middlewares=[driver_station_cache])
    app[ROBOT] = Robot()
    app[PEER] = SdkLink()
    app[DRIVER_CLIENTS] = set()
    app.router.add_get('/', home)
    app.router.add_get('/sim', simulator)
    app.router.add_get('/sim/state', state)
    app.router.add_get('/sim/drivers', drivers)
    app.router.add_get('/sim/driver-types', driver_types)
    app.router.add_get('/ds/assets/{version:[0-9a-f]{16}}/{filename:.*}', ds_asset)
    app.router.add_static('/ds/assets/', ROOT / 'ds' / 'assets')
    app.router.add_get('/ds', ds)
    app.router.add_get('/ds/', ds)
    app.router.add_get('/ds/hardware', ds)
    app.cleanup_ctx.append(lifecycle)
    return app



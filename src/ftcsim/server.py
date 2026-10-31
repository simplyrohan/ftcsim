#!/usr/bin/env python3
"""Central HTTP/WebSocket server. Run independently of the desktop SDK."""
import asyncio
from time import perf_counter
from contextlib import suppress
from pathlib import Path
from dataclasses import dataclass, field
from aiohttp import web, WSMsgType
from .physics.model import Robot
from .drivers import DRIVERS
from .mechanisms import MECHANISMS

ROOT = Path(__file__).resolve().parent
ROBOT = web.AppKey('robot', Robot)


@dataclass
class SdkLink:
    socket: object = None


PEER = web.AppKey('sdk_peer', SdkLink)


@dataclass
class Connections:
    stopping: bool = False
    sockets: dict = field(default_factory=dict)


CONNECTIONS = web.AppKey('connections', Connections)


async def simulator(request):
    connections = request.app[CONNECTIONS]
    if connections.stopping:
        raise web.HTTPServiceUnavailable(text='Simulator is stopping')
    if request.app[PEER].socket is not None:
        raise web.HTTPConflict(text='One SDK connection is already active')
    ws = web.WebSocketResponse(heartbeat=1, max_msg_size=1024 * 1024)
    # Claim ownership before yielding so two simultaneous upgrades cannot race.
    request.app[PEER].socket = ws
    connections.sockets[ws] = request.transport
    robot = request.app[ROBOT]
    try:
        await ws.prepare(request)
        robot.failsafe()
        robot.connected = True
        async for message in ws:
            if connections.stopping:
                break
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
        connections.sockets.pop(ws, None)
    return ws


async def state(request):
    return web.json_response(request.app[ROBOT].snapshot(), headers={'Cache-Control': 'no-store'})


async def drivers(request):
    """Live physical state, separate from the SDK-owned control connection."""
    connections = request.app[CONNECTIONS]
    if connections.stopping:
        raise web.HTTPServiceUnavailable(text='Simulator is stopping')
    origin = request.headers.get('Origin')
    if origin and origin != f'{request.scheme}://{request.host}':
        raise web.HTTPForbidden(text='Open the Driver Station from the simulator origin')
    ws = web.WebSocketResponse(heartbeat=5, max_msg_size=65536)
    robot = request.app[ROBOT]
    connections.sockets[ws] = request.transport

    async def publish():
        while not ws.closed and not connections.stopping:
            await ws.send_json(robot.snapshot())
            await asyncio.sleep(.1)

    task = None
    try:
        await ws.prepare(request)
        await ws.send_json(dict(type='drivers', drivers=DRIVERS.catalog()))
        task = asyncio.create_task(publish())
        async for message in ws:
            if connections.stopping:
                break
            if message.type == WSMsgType.TEXT:
                try:
                    data = message.json()
                    if isinstance(data, dict) and data.get('type') == 'ping':
                        if set(data) != {'type', 'id'} or type(data['id']) is not int:
                            raise ValueError('Invalid ping')
                        await ws.send_json(dict(type='pong', id=data['id']))
                        continue
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
        connections.sockets.pop(ws, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, ConnectionError):
                pass
            except RuntimeError:
                if not connections.stopping and not ws.closed:
                    raise
    return ws


async def driver_types(request):
    return web.json_response(DRIVERS.catalog(), headers={'Cache-Control': 'no-store'})


async def mechanism_types(request):
    return web.json_response(MECHANISMS.catalog(), headers={'Cache-Control': 'no-store'})


async def configure_mechanisms(request):
    started = perf_counter()
    origin = request.headers.get('Origin')
    if origin and origin != f'{request.scheme}://{request.host}':
        raise web.HTTPForbidden(text='Open the Driver Station from the simulator origin')
    try:
        data = await request.json()
        if not isinstance(data, dict) or set(data) != {'mechanisms'}:
            raise ValueError('Expected a mechanisms array')
        request.app[ROBOT].configure_mechanisms(data['mechanisms'])
    except (ValueError, TypeError) as error:
        return web.json_response(dict(message=str(error)), status=400)
    return web.json_response(request.app[ROBOT].snapshot(), headers={'Cache-Control': 'no-store',
                             'Server-Timing': f'mechanisms;dur={(perf_counter() - started) * 1000:.3f}'})


async def place_mechanism(request):
    origin = request.headers.get('Origin')
    if origin and origin != f'{request.scheme}://{request.host}':
        raise web.HTTPForbidden(text='Open the Driver Station from the simulator origin')
    try:
        data = await request.json()
        if not isinstance(data, dict) or set(data) != {'mechanism', 'x_mm', 'y_mm', 'heading_deg'}:
            raise ValueError('Expected mechanism, x_mm, y_mm and heading_deg')
        robot = request.app[ROBOT]
        mechanism = next((item for item in robot.mechanisms if item.name == data['mechanism']), None)
        if mechanism is None or not callable(getattr(mechanism, 'place', None)):
            raise ValueError('Choose an applied drivetrain for the start position')
        mechanism.place(data['x_mm'], data['y_mm'], data['heading_deg'])
    except (ValueError, TypeError) as error:
        return web.json_response(dict(message=str(error)), status=400)
    return web.json_response(robot.snapshot(), headers={'Cache-Control': 'no-store'})


async def ds(request):
    """Serve the SvelteKit static bundle and its client-side routes."""
    root = (ROOT / 'web').resolve()
    relative = request.match_info.get('path', '')
    source = (root / relative).resolve()
    if not source.is_relative_to(root):
        raise web.HTTPNotFound()
    if source.is_file():
        cache = 'public, max-age=31536000, immutable' if relative.startswith('_app/immutable/') else 'no-cache'
        if source.name.endswith('.html'):
            cache = 'no-store'
        return web.FileResponse(source, headers={'Cache-Control': cache})
    # Missing assets must be 404s, never an HTML fallback with the wrong MIME type.
    if relative.startswith('_app/') or Path(relative).suffix:
        raise web.HTTPNotFound()
    index = root / 'index.html'
    if not index.is_file():
        raise web.HTTPServiceUnavailable(text='Driver Station has not been built. Run python3 scripts/build_driver_station.py with Node.js 22.12+ installed.')
    return web.FileResponse(index, headers={'Cache-Control': 'no-store'})


async def home(request):
    raise web.HTTPFound('/ds')


async def shutdown(app):
    """Close upgrades before aiohttp waits for their request handlers to finish."""
    connections = app[CONNECTIONS]
    connections.stopping = True
    app[ROBOT].failsafe()

    async def close(ws, transport):
        try:
            # One bounded, concurrent grace period, even for peers that stop reading.
            await asyncio.wait_for(ws.close(code=1001, message=b'Simulator stopping', drain=False), timeout=.5)
        except (asyncio.TimeoutError, ConnectionError, RuntimeError):
            if transport is not None:
                transport.abort()

    await asyncio.gather(*(close(ws, transport) for ws, transport in tuple(connections.sockets.items())))


async def lifecycle(app):
    async def tick():
        loop = asyncio.get_running_loop()
        previous = loop.time()
        while not app[CONNECTIONS].stopping:
            await asyncio.sleep(.02)
            now = loop.time()
            if not app[CONNECTIONS].stopping:
                app[ROBOT].advance(min(now - previous, .1))
            previous = now
    task = asyncio.create_task(tick())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    app[ROBOT].failsafe()


def create_app(*, dev=False):
    """Create the simulator API, optionally leaving the UI to the Vite dev server."""
    app = web.Application(client_max_size=1024 * 1024)
    app[ROBOT] = Robot()
    app[PEER] = SdkLink()
    app[CONNECTIONS] = Connections()
    app.router.add_get('/sim', simulator)
    app.router.add_get('/sim/state', state)
    app.router.add_get('/sim/drivers', drivers)
    app.router.add_get('/sim/driver-types', driver_types)
    app.router.add_get('/sim/mechanism-types', mechanism_types)
    app.router.add_post('/sim/mechanisms', configure_mechanisms)
    app.router.add_post('/sim/mechanisms/place', place_mechanism)
    if not dev:
        app.router.add_get('/', home)
        app.router.add_get('/ds', ds)
        app.router.add_get('/ds/{path:.*}', ds)
    app.cleanup_ctx.append(lifecycle)
    app.on_shutdown.append(shutdown)
    return app



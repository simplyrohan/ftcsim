#!/usr/bin/env python3
"""Central HTTP/WebSocket server. Run independently of the desktop SDK."""
import argparse
import asyncio
from contextlib import suppress
from pathlib import Path
from dataclasses import dataclass
from aiohttp import web, WSMsgType
from .physics.model import Robot

ROOT = Path(__file__).resolve().parent
ROBOT = web.AppKey('robot', Robot)


@dataclass
class SdkLink:
    socket: object = None


PEER = web.AppKey('sdk_peer', SdkLink)


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


async def ds(request):
    # This route is static: no Driver Station state or SDK proxy exists in Python.
    return web.FileResponse(ROOT / 'ds' / 'index.html', headers={'Cache-Control': 'no-store'})


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


def create_app():
    app = web.Application(client_max_size=1024 * 1024)
    app[ROBOT] = Robot()
    app[PEER] = SdkLink()
    app.router.add_get('/', home)
    app.router.add_get('/sim', simulator)
    app.router.add_get('/sim/state', state)
    app.router.add_get('/ds', ds)
    app.router.add_get('/ds/', ds)
    app.cleanup_ctx.append(lifecycle)
    return app



# Python simulator server

Python owns the physical model and serves a static Driver Station page. It neither
launches a JVM nor proxies Driver Station traffic. All Java belongs to `../sdk/`.

```sh
python3 -m pip install -r requirements.txt
python3 server.py
```

The server binds IPv4 loopback on port 9015. Use `--port` to change it and pass the
matching `--sim` URL to the desktop SDK. The browser SDK endpoint is editable in
the page; `?sdk=1116` changes its initial port.

| Endpoint | Purpose |
| --- | --- |
| `GET /sim` with WebSocket upgrade | One long-lived SDK connection; Lynx JSON requests and correlated replies. |
| `GET /sim/state` | Read-only motor state for the physical display. |
| `GET /ds` | Static browser Driver Station. |
| `GET /` | Redirect to `/ds`. |

`physics/registers.py` preserves SDK payload layouts. `physics/model.py` adds an
independent model per hub: four motors, enable/mode, power or target velocity,
encoder integration, reset, target position, and bulk reads. Full power means
2800 ticks/second; acceleration is instantaneous. Basic servo/PWM/DIO registers
remain for compatibility; no robot pose or localization is calculated.

Unsupported commands return NACK 255. Malformed requests return a protocol error.
When the SDK socket closes or its WebSocket heartbeat fails, motor/servo outputs
are disabled. The server accepts only one SDK connection so hardware ownership is
unambiguous. It can serve multiple static browser pages.

The DS page connects directly to SDK port 1115, sends lifecycle/configuration and
two gamepads, and renders returned telemetry/status. Keyboard, virtual controls,
and browser Gamepad API inputs are available. SDK clients without an Origin header
are also supported. The SDK permits the loopback simulator page origin and assigns
one controller; other connections observe. Reconnect an observer after the previous
controller disconnects to take control.

Build the SDK classpaths first, then run:

```sh
python3 -m unittest discover -s tests -v
```

Tests use temporary ports and launch the built desktop SDK only as a test fixture.
A missing SDK build skips those integration tests; the server itself never invokes
Java. See [the protocol](../PROTOCOL.md) for message formats and limitations.

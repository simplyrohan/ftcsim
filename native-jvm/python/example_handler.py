"""Example: wire your own simulator into every command at this boundary."""
import struct

def handle(request, state):
    name = request['command'].rsplit('.', 1)[-1]
    if name == 'LynxGetMotorEncoderPositionCommand':
        motor = bytes.fromhex(request['payload'])[0]
        # Replace this with a position from your physics engine.
        return struct.pack('<i', 1234 + motor)
    return None  # Use the built-in register model (unknown commands NACK).

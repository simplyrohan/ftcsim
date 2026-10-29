"""Read-only actuator followers for user-supplied visual models."""
from .base import Mechanism
from ..drivers import DCMotor, Servo
from ..drivers.base import number


class CustomMechanism(Mechanism):
    kind = 'custom'
    display_name = 'Custom mechanism'
    description = 'Visual actuator follower. Reads a motor or servo without driving hardware or sensors.'
    exclusive = False
    driver_slots = {'actuator': dict(label='Motor or servo', driver=(DCMotor, Servo), required=False)}
    option_metadata = {
        'motion': dict(label='Movement', choices=[dict(value='rotation', label='Rotation'), dict(value='translation', label='Translation')]),
        'axis': dict(label='Local motion axis', choices=[dict(value='x', label='X · forward'), dict(value='y', label='Y · left'), dict(value='z', label='Z · up')]),
        'direction': dict(label='Direction', choices=[dict(value=1, label='Forward'), dict(value=-1, label='Reversed')]),
        'travel': dict(label='Travel per motor revolution / full servo range', min=0),
        'input_zero': dict(label='Input at starting pose'),
    }

    def __init__(self, name, drivers, motion='rotation', axis='z', direction=1, travel=360, input_zero=0):
        super().__init__(name, drivers)
        if motion not in ('rotation', 'translation') or axis not in ('x', 'y', 'z'):
            raise ValueError('Invalid custom mechanism motion or axis')
        if type(direction) is not int or direction not in (-1, 1):
            raise ValueError('Direction must be 1 or -1')
        self.motion_type, self.axis, self.direction = motion, axis, direction
        self.travel = number(travel, 'travel')
        if self.travel < 0:
            raise ValueError('Travel must be nonnegative')
        self.input_zero = number(input_zero, 'input_zero')

    def advance(self, dt):
        pass

    def state(self):
        actuator = self.drivers.get('actuator')
        position = (actuator.position / actuator.ticks_per_revolution * actuator.direction
                    if isinstance(actuator, DCMotor) else actuator.position if actuator else self.input_zero)
        return dict(input_position=position, displacement=(position-self.input_zero)*self.travel*self.direction,
                    motion=self.motion_type, axis=self.axis, bound=actuator is not None)

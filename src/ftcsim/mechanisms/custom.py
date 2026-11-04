"""Read-only actuator followers for user-supplied visual models."""
from .base import Mechanism
from ..drivers import DCMotor, Servo, CRServo
from ..drivers.base import number


class CustomMechanism(Mechanism):
    kind = 'custom'
    display_name = 'Custom mechanism'
    description = 'Visual actuator follower. Motors and CR servos supply shaft revolutions; positional servos supply 0–1 position.'
    exclusive = False
    driver_slots = {'actuator': {'label': 'Motor or servo', 'driver': (DCMotor, Servo, CRServo), 'required': False}}
    option_metadata = {
        'motion': {'label': 'Movement', 'choices': [{'value': 'rotation', 'label': 'Rotation'}, {'value': 'translation', 'label': 'Translation'}]},
        'axis': {'label': 'Local motion axis', 'choices': [{'value': 'x', 'label': 'X · forward'}, {'value': 'y', 'label': 'Y · left'}, {'value': 'z', 'label': 'Z · up'}]},
        'direction': {'label': 'Direction', 'choices': [{'value': 1, 'label': 'Forward'}, {'value': -1, 'label': 'Reversed'}]},
        'travel': {'label': 'Travel per shaft revolution / full positional servo range', 'min': 0},
        'input_zero': {'label': 'Input at starting pose'},
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
        return {'input_position': position, 'displacement': (position-self.input_zero)*self.travel*self.direction,
                'motion': self.motion_type, 'axis': self.axis, 'bound': actuator is not None}

"""Internal driver catalog and strict topology construction; no plugin loading."""
import inspect
from .base import Driver
from .motor import DCMotor
from .servo import Servo
from .cr_servo import CRServo
from .odometry import OdometryPod
from .pinpoint import GoBildaPinpoint


class DriverRegistry:
    def __init__(self):
        self.types = {}

    def register(self, driver):
        if not issubclass(driver, Driver) or driver.kind in self.types:
            raise ValueError('Invalid or duplicate driver registration')
        self.types[driver.kind] = driver
        return driver

    def create(self, definition, names, parent=None):
        if not isinstance(definition, dict):
            raise ValueError('Device definition must be an object')
        allowed = {'name', 'type', 'module', 'port', 'options', 'children'}
        if definition.keys() - allowed:
            raise ValueError(f'Unknown device fields: {definition.keys() - allowed}')
        name, kind, port = definition['name'], definition['type'], definition['port']
        if not isinstance(name, str) or not name.strip() or name in names or name.startswith('hub') and name[3:].isdigit():
            raise ValueError(f'Duplicate, empty, or reserved device name: {name}')
        cls = self.types.get(kind)
        if cls is None:
            raise ValueError(f'Unknown driver type: {kind}')
        if parent:
            if port not in parent.child_ports or cls.connection != parent.child_connections.get(port) or 'module' in definition:
                raise ValueError(f'Invalid {parent.kind} child connection {port}')
        else:
            limit = 6 if cls.connection == 'servo' else 4
            if type(port) is not int or not 0 <= port < limit:
                raise ValueError(f'Invalid {kind} hub port')
        options = definition.get('options', {})
        if not isinstance(options, dict):
            raise ValueError(f'Unknown options for {kind}')
        if hasattr(cls, 'normalize_options'):
            options = cls.normalize_options(options)
        parameters = inspect.signature(cls.__init__).parameters
        if not isinstance(options, dict) or options.keys() - (parameters.keys() - {'self', 'name', 'port'}):
            raise ValueError(f'Unknown options for {kind}')
        options = {**parent.child_defaults.get(port, {}), **options} if parent else options
        children = definition.get('children', [])
        if not isinstance(children, list) or len(children) > len(cls.child_ports):
            raise ValueError(f'Invalid children for {kind}')
        names.add(name)
        instance = cls(name, port, **options)
        for child in children:
            driver = self.create(child, names, instance)
            instance.attach(driver.port, driver)
        return instance

    def catalog(self):
        catalog = []
        for kind, cls in self.types.items():
            options = []
            for name, parameter in inspect.signature(cls.__init__).parameters.items():
                if name in ('self', 'name', 'port'):
                    continue
                default = parameter.default
                if default is inspect.Parameter.empty:
                    raise ValueError(f'{kind}: configurable options need defaults')
                metadata = getattr(cls, 'option_metadata', {}).get(name, {})
                option = {'name': name, 'type': 'number' if isinstance(default, (int, float)) else 'text',
                          'default': default, 'label': name.replace('_', ' ').title()}
                option.update(metadata)
                options.append(option)
            catalog.append({'type': kind, 'label': getattr(cls, 'display_name', kind),
                            'connection': cls.connection, 'ports': 6 if cls.connection == 'servo' else 4,
                            'child_ports': cls.child_ports, 'child_connections': cls.child_connections,
                            'child_defaults': cls.child_defaults, 'options': options,
                            'presets': getattr(cls, 'presets', ())})
        return catalog


DRIVERS = DriverRegistry()
for driver in (DCMotor, Servo, CRServo, OdometryPod, GoBildaPinpoint):
    DRIVERS.register(driver)

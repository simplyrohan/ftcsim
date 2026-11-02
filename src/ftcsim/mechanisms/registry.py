"""Built-in mechanism catalog, driver binding, and exclusive resource validation."""
import inspect
from .base import Mechanism
from .mecanum import MecanumDrivetrain
from .custom import CustomMechanism


class MechanismRegistry:
    def __init__(self):
        self.types = {}

    def register(self, mechanism):
        if not issubclass(mechanism, Mechanism) or not mechanism.kind or mechanism.kind in self.types:
            raise ValueError('Invalid or duplicate mechanism registration')
        self.types[mechanism.kind] = mechanism
        return mechanism

    def create_all(self, definitions, drivers):
        if not isinstance(definitions, list) or len(definitions) > 64:
            raise ValueError('Expected a list of at most 64 mechanisms')
        names, claimed, instances = set(), set(), []
        for definition in definitions:
            if not isinstance(definition, dict) or definition.keys() - {'name', 'type', 'drivers', 'options'}:
                raise ValueError('Invalid mechanism definition')
            name, kind = definition.get('name'), definition.get('type')
            if not isinstance(name, str) or not name.strip() or name in names:
                raise ValueError('Mechanism names must be nonempty and unique')
            cls = self.types.get(kind) if isinstance(kind, str) else None
            if cls is None:
                raise ValueError(f'Unknown mechanism type: {kind}')
            bindings = definition.get('drivers')
            if not isinstance(bindings, dict) or bindings.keys() - cls.driver_slots.keys():
                raise ValueError(f'{name}: invalid driver bindings')
            bound = {}
            for slot, spec in cls.driver_slots.items():
                reference = bindings.get(slot)
                if reference is None and not spec['required']:
                    continue
                driver = drivers.get(reference) if isinstance(reference, str) else None
                if not isinstance(driver, spec['driver']):
                    types = spec['driver'] if isinstance(spec['driver'], tuple) else (spec['driver'],)
                    expected = ' or '.join(driver_type.kind for driver_type in types)
                    raise ValueError(f'{name}: {spec["label"]} must reference a configured {expected} driver')
                bound[slot] = driver
            options = definition.get('options', {})
            parameters = inspect.signature(cls.__init__).parameters.keys() - {'self', 'name', 'drivers'}
            if not isinstance(options, dict) or options.keys() - parameters:
                raise ValueError(f'{name}: unknown mechanism options')
            instance = cls(name, bound, **options)
            consumed = instance.consumed_drivers
            if len(set(consumed)) != len(consumed) or claimed.intersection(consumed):
                raise ValueError(f'{name}: each driver can be connected to only one mechanism input')
            claimed.update(consumed)
            names.add(name)
            instances.append(instance)
        return instances

    def catalog(self):
        result = []
        for kind, cls in self.types.items():
            options = []
            for name, parameter in inspect.signature(cls.__init__).parameters.items():
                if name in ('self', 'name', 'drivers'):
                    continue
                if parameter.default is inspect.Parameter.empty:
                    raise ValueError(f'{kind}: configurable options need defaults')
                option = {'name': name, 'label': name.replace('_', ' ').title(), 'default': parameter.default,
                          'type': 'number' if isinstance(parameter.default, (int, float)) else 'text'}
                option.update(cls.option_metadata.get(name, {}))
                options.append(option)
            slots = [{'name': name, 'label': spec['label'], 'types': [driver.kind for driver in (spec['driver'] if isinstance(spec['driver'], tuple) else (spec['driver'],))], 'required': spec['required'],
                      'children': spec.get('children', {})}
                     for name, spec in cls.driver_slots.items()]
            result.append({'type': kind, 'label': cls.display_name, 'description': getattr(cls, 'description', ''),
                           'drivers': slots, 'options': options, 'exclusive': getattr(cls, 'exclusive', True)})
        return result


MECHANISMS = MechanismRegistry()
MECHANISMS.register(MecanumDrivetrain)

MECHANISMS.register(CustomMechanism)

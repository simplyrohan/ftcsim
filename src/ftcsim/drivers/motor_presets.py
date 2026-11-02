"""goBILDA 5203 12 V specs; ticks are quadrature counts per output-shaft turn."""
_SPECS = (
    ('0001', '1:1', 6000, 28),
    ('0003', '3.7:1', 1620, 103.8),
    ('0005', '5.2:1', 1150, 145.1),
    ('0014', '13.7:1', 435, 384.5),
    ('0019', '19.2:1', 312, 537.7),
    ('0027', '26.9:1', 223, 751.8),
    ('0051', '50.9:1', 117, 1425.1),
    ('0071', '71.2:1', 84, 1993.6),
    ('0100', '99.5:1', 60, 2786.2),
    ('0139', '139:1', 43, 3895.9),
    ('0188', '188:1', 30, 5281.1),
)

GOBILDA_PRESETS = tuple(
    {'id': f'gobilda-5203-{rpm}', 'label': f'goBILDA Yellow Jacket · {rpm} RPM ({ratio})',
     'options': {'max_rpm': rpm, 'ticks_per_revolution': ticks},
     'source': (f'https://www.gobilda.com/content/spec_sheets/5203-2402-{sku}_spec_sheet.pdf'
                 if sku != '0001' else 'https://www.gobilda.com/5203-series-yellow-jacket-motor-1-1-ratio-24mm-length-8mm-rex-shaft-6000-rpm-3-3-5v-encoder/')}
    for sku, ratio, rpm, ticks in _SPECS
)

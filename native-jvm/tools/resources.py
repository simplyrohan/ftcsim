"""Generate desktop R symbols and a string lookup table; no Android resource compiler."""
from pathlib import Path
import xml.etree.ElementTree as ET
import re
root = Path(__file__).resolve().parents[2]
modules = ['RobotCore','RobotServer','Hardware','Inspection','FtcCommon','Vision','Blocks','OnBotJava']
symbols = {}
strings = {}
styleables = {}
def add(kind,name):
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    symbols.setdefault(kind, set()).add(name)
    return name
for module in modules:
    for path in (root/module/'src/main/res').rglob('*'):
        if not path.is_file(): continue
        kind = path.parent.name.split('-')[0]
        if kind != 'values': add(kind, path.name.split('.')[0])
        if path.suffix == '.xml':
            tree = ET.parse(path)
            if kind == 'values':
                for child in tree.getroot():
                    name=child.get('name')
                    if not name: continue
                    tag=child.get('type', child.tag)
                    if tag in ('string-array','integer-array'): tag='array'
                    if tag == 'declare-styleable':
                        attrs = [add('attr', child_attr.get('name')) for child_attr in child if child_attr.tag == 'attr']
                        styleables[name] = attrs
                        continue
                    add(tag,name)
                    if tag == 'string' and path.parent.name == 'values': strings[name]=''.join(child.itertext())
            for elem in tree.iter():
                for val in elem.attrib.values():
                    if val.startswith('@+id/'): add('id',val[5:])
# appcompat fields referenced directly by SDK code are compile-time only.
output = root/'native-jvm/build/generated'
output.mkdir(parents=True,exist_ok=True)
packages = ['com.qualcomm.robotcore','com.qualcomm.hardware','org.firstinspires.inspection','org.firstinspires.ftc.robotcore.internal.webserver','com.qualcomm.ftccommon','org.firstinspires.ftc.vision','org.firstinspires.ftc.apriltag','com.google.blocks','com.google.blocks.ftcrobotcontroller.onbotjava']
index=1
values={}
for kind in sorted(symbols):
    for name in sorted(symbols[kind]): values[kind,name]=index; index+=1
for package in packages:
    path = output/Path(package.replace('.','/'))/'R.java'; path.parent.mkdir(parents=True,exist_ok=True)
    text='package '+package+';\npublic final class R {\n'
    for kind in sorted(symbols):
        if kind == 'declare-styleable': continue
        text+='public static final class '+kind+' {\n'
        for name in sorted(symbols[kind]): text+=f'public static final int {name} = {values[kind,name]};\n'
        text+='}\n'
    text+='public static final class styleable {\n'
    for name, attrs in sorted(styleables.items()):
        text+='public static final int[] '+name+' = new int[]{'+','.join(str(values['attr',attr]) for attr in attrs)+'};\n'
        for i, attr in enumerate(attrs): text+=f'public static final int {name}_{attr} = {i};\n'
    text+='}\n'
    path.write_text(text+'}\n')
import json
path=output/'ftcsim/jvm/ResourceStrings.java';path.parent.mkdir(parents=True,exist_ok=True)
text='package ftcsim.jvm;\npublic final class ResourceStrings { public static String get(int id) { switch(id) {\n'
for name, value in sorted(strings.items()): text+=f'case {values["string",name]}: return {json.dumps(value,ensure_ascii=True)};\n'
path.write_text(text+'default: return "resource:"+id; } } }\n')

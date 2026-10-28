#!/usr/bin/env python3
"""Recreate editable SDK modules from official Maven sources and AARs."""
import hashlib, io, json, pathlib, urllib.request, zipfile, xml.etree.ElementTree as ET
ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
ET.register_namespace('tools', 'http://schemas.android.com/tools')
ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = '12.0.0'
MODULES = ['RobotCore', 'RobotServer', 'Hardware', 'Inspection', 'FtcCommon', 'Vision', 'Blocks', 'OnBotJava']
NS = {'m': 'http://maven.apache.org/POM/4.0.0'}
# Source-level edges not represented by runtime-only published dependencies.
EDGES = {'RobotCore': [], 'RobotServer': ['RobotCore'], 'Hardware': ['RobotCore'], 'Inspection': ['Hardware', 'RobotCore'], 'FtcCommon': ['Hardware', 'Inspection', 'RobotCore', 'RobotServer'], 'Vision': ['RobotCore'], 'Blocks': ['RobotCore', 'RobotServer', 'FtcCommon', 'Hardware', 'Vision'], 'OnBotJava': ['RobotCore', 'RobotServer', 'Blocks']}
def main():
    lock_path = ROOT / 'sdk-artifacts.sha256.json'
    expected = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    lock = {}
    for module in MODULES:
        print('Extracting', module, flush=True)
        base = f'https://repo.maven.apache.org/maven2/org/firstinspires/ftc/{module}/{VERSION}/{module}-{VERSION}'
        blobs = {}
        for suffix in ['.pom', '.aar', '-sources.jar']:
            url = base + suffix
            blobs[suffix] = urllib.request.urlopen(url).read()
            lock[url] = hashlib.sha256(blobs[suffix]).hexdigest()
            if url in expected and expected[url] != lock[url]:
                raise ValueError('Artifact checksum mismatch: ' + url)
        directory = ROOT / module
        directory.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(blobs['.aar'])) as archive:
            manifest = archive.read('AndroidManifest.xml')
            namespace = ET.fromstring(manifest).attrib['package']
            for entry in archive.infolist():
                name = entry.filename
                if entry.is_dir(): continue
                if name == 'AndroidManifest.xml': target = 'src/main/AndroidManifest.xml'
                elif name.startswith(('res/', 'assets/')): target = 'src/main/' + name
                elif name.startswith('jni/'): target = 'src/main/jniLibs/' + name[4:]
                elif name.startswith('libs/'): target = name
                elif name == 'proguard.txt': target = 'consumer-rules.pro'
                else: continue
                path = directory / target
                path.parent.mkdir(parents=True, exist_ok=True)
                data = archive.read(entry)
                if name == 'AndroidManifest.xml':
                    tree = ET.fromstring(data)
                    tree.attrib.pop('package', None)
                    data = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
                path.write_bytes(data)
        with zipfile.ZipFile(io.BytesIO(blobs['-sources.jar'])) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or entry.filename.startswith('META-INF/'): continue
                path = directory / 'src/main/java' / entry.filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(entry))
        deps = [f"    api project(':{edge}')" for edge in EDGES[module]]
        pom = ET.fromstring(blobs['.pom'])
        for dep in pom.findall('m:dependencies/m:dependency', NS):
            group, artifact, version = [dep.find('m:' + key, NS).text for key in ['groupId', 'artifactId', 'version']]
            if group == 'org.firstinspires.ftc':
                if artifact not in EDGES[module]: deps.append(f"    api project(':{artifact}')")
            else: deps.append(f"    api '{group}:{artifact}:{version}'")
        deps.append("    api fileTree(dir: 'libs', include: ['*.jar'])")
        (directory / 'build.gradle').write_text("apply plugin: 'com.android.library'\n\nandroid {\n    namespace '" + namespace + "'\n    compileSdkVersion 30\n    defaultConfig {\n        minSdkVersion 24\n        targetSdkVersion 28\n" + ("        consumerProguardFiles 'consumer-rules.pro'\n" if (directory / 'consumer-rules.pro').exists() else '') + "    }\n    buildFeatures { buildConfig = false }\n    compileOptions {\n        sourceCompatibility JavaVersion.VERSION_1_8\n        targetCompatibility JavaVersion.VERSION_1_8\n    }\n}\n\ndependencies {\n" + '\n'.join(deps) + '\n}\n')
    (ROOT / 'sdk-artifacts.sha256.json').write_text(json.dumps(lock, indent=2) + '\n')
if __name__ == '__main__': main()

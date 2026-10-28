#!/usr/bin/env python3
"""Install a desktop TeamCodeSim target into an FTC project. with the packaged SDK.

Run from the FTC project root:
    ftcsim --wizard
    ftcsim --wizard --yes --dry-run

Robot sources/build files inside TeamCode are never edited. The default SDK mode
links the bundled compiled SDK. --copy-sdk copies its binaries into the project.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from rich.console import Console
console = Console(highlight=False, markup=False)
print = console.print

VERSION = '0.1.0'
STATE = '.ftcsim/install.json'
SKIP_DIRS = {'.git', '.gradle', '.idea', '.venv', '__pycache__', 'build', 'out', '.kotlin'}


class WizardError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def block(text: str, key: str, body: str, comment: str = '//') -> str:
    newline = '\r\n' if '\r\n' in text else '\n'
    begin, end = f'{comment} <ftcsim:{key}>', f'{comment} </ftcsim:{key}>'
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise WizardError(f'Broken/duplicate managed block: {key}')
    value = newline.join([begin, *body.strip().splitlines(), end, ''])
    pattern = re.compile(r'^' + re.escape(begin) + r'\r?\n.*?^' + re.escape(end) + r'(?:\r?\n|$)', re.M | re.S)
    match = pattern.search(text)
    if begin in text and match is None:
        raise WizardError(f'Malformed managed block: {key}')
    if match:
        return text[:match.start()] + value + text[match.end():]
    return text + (newline if text and not text.endswith('\n') else '') + newline + value


def without_block(text: str, key: str, comment: str = '//') -> str:
    return re.sub(r'^' + re.escape(f'{comment} <ftcsim:{key}>') + r'\r?\n.*?^' +
                  re.escape(f'{comment} </ftcsim:{key}>') + r'(?:\r?\n|$)', '', text, flags=re.M | re.S)


def gradle_file(root: Path, stem: str) -> Path:
    candidates = [root / (stem + '.gradle.kts'), root / (stem + '.gradle')]
    found = [p for p in candidates if p.is_file()]
    if len(found) != 1:
        raise WizardError(f'Expected one {stem}.gradle or {stem}.gradle.kts in {root}')
    return found[0]


def safe_path(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise WizardError(f'Unsafe generated path: {name}')
    path = root / relative
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise WizardError(f'Refusing to edit through a symlink: {cursor}')
        cursor = cursor.parent
    if path.exists() and not path.is_file():
        raise WizardError(f'Expected a file, found a directory: {path}')
    return path


def owned_name(name: str) -> bool:
    return (name.startswith('TeamCodeSim/') or name.startswith('.ftcsim/distribution/') or
            name in {'.run/FTCSim_Simulator.run.xml', '.run/FTCSim_Backend.run.xml', '.run/FTCSim_Robot.run.xml'})


def sdk_directory(value: str | None) -> Path:
    path = Path(value).expanduser() if value else Path(__file__).parent / 'sdk'
    if not (path / 'libs/ftc-sdk-jvm-12.0.0.jar').is_file():
        raise WizardError('Compiled SDK missing. Build the package first (python scripts/build_sdk.py), or supply --sdk with a compiled bundle.')
    return path.resolve()


def kotlin_setup(root: Path, has_kotlin: bool, requested: str | None) -> str:
    if not has_kotlin:
        return ''
    texts = '\n'.join(p.read_text() for p in (root / 'build.gradle', root / 'build.gradle.kts') if p.is_file())
    inherited = bool(re.search(r'kotlin-gradle-plugin|org\.jetbrains\.kotlin|kotlin\(["\'](?:android|jvm)["\']', texts))
    versions = re.findall(r'(?:kotlinVersion|kotlin_version)\s*=\s*["\']([\d.]+)["\']', texts)
    versions += re.findall(r'(?:org\.jetbrains\.kotlin\.(?:android|jvm)|kotlin-gradle-plugin)["\']?\)?\s*(?:version|:)\s*["\']?([\d.]+)', texts)
    known = versions[0] if versions else None
    if requested and not re.fullmatch(r'\d+\.\d+(?:\.\d+)?(?:[-.][A-Za-z0-9]+)*', requested):
        raise WizardError('Invalid Kotlin version')
    if inherited:
        if requested and known and requested != known:
            raise WizardError(f'Root already supplies Kotlin {known}; do not request {requested}.')
        return "    id 'org.jetbrains.kotlin.jvm'\n"
    if not requested:
        raise WizardError('Kotlin sources found but no root Kotlin plugin was detected. Supply --kotlin-version matching your Android compiler.')
    return f"    id 'org.jetbrains.kotlin.jvm' version '{requested}'\n"


def discover_opmodes(root: Path) -> list[str]:
    result = set()
    for folder in ('TeamCode/src/main/java', 'TeamCode/src/main/kotlin'):
        directory = root / folder
        if not directory.exists():
            continue
        for path in directory.rglob('*'):
            if path.suffix not in ('.java', '.kt'):
                continue
            text = path.read_text()
            package = re.search(r'^\s*package\s+([\w.]+)', text, re.M)
            if not package:
                continue
            # Strip comments/strings for brace depth; keep character offsets stable.
            scrubbed = re.sub(r'/\*.*?\*/|//[^\n]*|""".*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                              lambda m: ' ' * len(m[0]), text, flags=re.S)
            last = 0
            for match in re.finditer(r'\bclass\s+(\w+)', scrubbed):
                prefix = scrubbed[:match.start()]
                if prefix.count('{') != prefix.count('}'):
                    continue
                start = max(last, scrubbed.rfind('}', 0, match.start()) + 1)
                annotations = re.findall(r'@(?:[\w]+\.)*(\w+)', scrubbed[start:match.start()])
                if ('TeleOp' in annotations or 'Autonomous' in annotations) and 'Disabled' not in annotations:
                    result.add(package[1] + '.' + match[1])
                last = match.end()
    return sorted(result)


def robot_xml(path: Path) -> dict:
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as error:
        raise WizardError(f'Cannot read robot XML: {error}') from error
    devices, unsupported = [], []
    names, ports = set(), set()
    def visit(element, module=None):
        if element.get('enabled', 'true').lower() == 'false':
            return
        tag = element.tag.rsplit('}', 1)[-1]
        if tag == 'LynxModule':
            try:
                module = int(element.get('port', ''))
            except ValueError as error:
                raise WizardError('LynxModule needs an integer address in its port attribute') from error
            if not 1 <= module <= 254:
                raise WizardError('Lynx module address must be 1..254')
        elif module is not None and element.get('name') and element.get('port') is not None:
            lowered = tag.lower()
            kind = ('servo' if lowered in ('servo', 'servofullrange') else
                    'motor' if 'motor' in lowered or lowered.startswith(('gobilda5202', 'neverest', 'tetrix')) else None)
            try:
                port = int(element.get('port'))
            except ValueError as error:
                raise WizardError(f'Invalid port for {element.get("name")}') from error
            item = {'name': element.get('name').strip(), 'type': kind or tag, 'module': module, 'port': port}
            if kind:
                key = (module, kind, port)
                if not 0 <= port < (4 if kind == 'motor' else 6):
                    raise WizardError(f'Invalid {kind} port: {item}')
                if not item['name'] or item['name'] in names or key in ports or re.fullmatch(r'hub\d+', item['name']):
                    raise WizardError(f'Duplicate/reserved name or port: {item}')
                names.add(item['name']); ports.add(key); devices.append(item)
            else:
                unsupported.append(item)
        for child in element:
            visit(child, module)
    visit(tree.getroot())
    return {'source': str(path.resolve()), 'devices': devices, 'unsupportedDevices': unsupported}


def run_xml(name: str, task: str | None = None, module: str | None = None) -> bytes:
    root = ET.Element('component', name='ProjectRunConfigurationManager')
    config = ET.SubElement(root, 'configuration', default='false', name=name,
                           type='GradleRunConfiguration' if task else 'AndroidRunConfigurationType',
                           factoryName='Gradle' if task else 'Android App')
    if task:
        settings = ET.SubElement(config, 'ExternalSystemSettings')
        for key, value in [('executionName', name), ('externalProjectPath', '$PROJECT_DIR$'),
                           ('externalSystemIdString', 'GRADLE'), ('scriptParameters', '')]:
            ET.SubElement(settings, 'option', name=key, value=value)
        items = ET.SubElement(ET.SubElement(settings, 'option', name='taskNames'), 'list')
        ET.SubElement(items, 'option', value=task)
    else:
        ET.SubElement(config, 'module', name=module)
        ET.SubElement(config, 'option', name='DEPLOY', value='true')
        ET.SubElement(config, 'option', name='MODE', value='default_activity')
    method = ET.SubElement(config, 'method', v='2')
    if not task:
        ET.SubElement(method, 'option', name='Android.Gradle.BeforeRunTask', enabled='true')
    ET.indent(root)
    return ET.tostring(root, encoding='utf-8') + b'\n'


@dataclass
class Change:
    name: str
    before: bytes | None
    after: bytes | None
    mode: int = 0o644


class Plan:
    def __init__(self, root: Path, force: bool):
        self.root, self.force = root, force
        state_path = safe_path(root, STATE)
        try:
            self.old = json.loads(state_path.read_text()) if state_path.exists() else {}
        except (ValueError, OSError) as error:
            raise WizardError(f'Invalid installer state: {error}') from error
        if self.old and self.old.get('format') != 1:
            raise WizardError('Unsupported installer-state format')
        self.managed = {}
        self.changes = []

    def put(self, name: str, content: str | bytes, *, managed=False, mode=0o644):
        path = safe_path(self.root, name)
        before = path.read_bytes() if path.is_file() else None
        after = content.encode() if isinstance(content, str) else content
        if managed:
            if not owned_name(name):
                raise WizardError(f'Invalid managed filename: {name}')
            prior = self.old.get('managed', {}).get(name)
            if before is not None and before != after and not self.force:
                if prior is None or digest(before) != prior:
                    raise WizardError(f'{name} has user changes or is not wizard-owned. Use --force to back it up and replace it.')
            self.managed[name] = digest(after)
        if before != after:
            self.changes.append(Change(name, before, after, path.stat().st_mode & 0o777 if path.exists() else mode))

    def state(self, sdk: Path, mode: str):
        for name, previous in self.old.get('managed', {}).items():
            if not owned_name(name):
                raise WizardError(f'Invalid installer-state filename: {name}')
            if name not in self.managed:
                path = safe_path(self.root, name)
                if path.exists():
                    before = path.read_bytes()
                    if digest(before) != previous and not self.force:
                        raise WizardError(f'Stale managed file was edited: {name}; use --force to back up and remove it.')
                    self.changes.append(Change(name, before, None, path.stat().st_mode & 0o777))
        value = {'format': 1, 'wizard': VERSION, 'source_sdk': str(sdk), 'sdk_mode': mode, 'managed': self.managed}
        self.put(STATE, json.dumps(value, indent=2, sort_keys=True) + '\n')

    def apply(self) -> Path | None:
        if not self.changes:
            return None
        meta = self.root / '.ftcsim'
        safe_path(self.root, '.ftcsim/.probe')
        meta.mkdir(exist_ok=True)
        backup = meta / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
        safe_path(self.root, (backup / 'changes.json').relative_to(self.root).as_posix())
        backup.mkdir(parents=True)
        for change in self.changes:
            if change.before is not None:
                path = backup / change.name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(change.before)
                path.chmod(change.mode)
        (backup / 'changes.json').write_text(json.dumps({
            'created': [c.name for c in self.changes if c.before is None],
            'modified': [c.name for c in self.changes if c.before is not None],
        }, indent=2) + '\n')
        completed = []
        try:
            with tempfile.TemporaryDirectory(prefix='stage-', dir=meta) as folder:
                stage = Path(folder)
                for index, change in enumerate(self.changes):
                    if change.after is not None:
                        path = stage / str(index)
                        path.write_bytes(change.after)
                        path.chmod(change.mode)
                for index, change in enumerate(self.changes):
                    target = safe_path(self.root, change.name)
                    # Detect edits made after planning/confirmation instead of overwriting them.
                    current = target.read_bytes() if target.exists() else None
                    if current != change.before:
                        raise WizardError(f'File changed during installation: {change.name}')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if change.after is None:
                        target.unlink()
                    else:
                        os.replace(stage / str(index), target)
                    completed.append(change)
        except BaseException:
            for change in reversed(completed):
                target = self.root / change.name
                if change.before is None:
                    target.unlink(missing_ok=True)
                else:
                    shutil.copy2(backup / change.name, target)
            raise
        return backup


def tree_files(root: Path):
    for directory, folders, files in os.walk(root):
        folders[:] = [name for name in folders if name not in SKIP_DIRS]
        for name in folders:
            if (Path(directory) / name).is_symlink():
                raise WizardError(f'Cannot vendor SDK symlink: {Path(directory) / name}')
        for name in sorted(files):
            path = Path(directory) / name
            if path.is_symlink():
                raise WizardError(f'Cannot vendor SDK symlink: {path}')
            if name in ('local.properties', '.DS_Store') or name.endswith(('.pyc', '.log')):
                continue
            yield path


def make_plan(args) -> tuple[Plan, list[str]]:
    root = args.project.resolve()
    if not (root / 'TeamCode/src/main').is_dir():
        raise WizardError('Run from an FTC project root containing TeamCode/src/main (or use --project).')
    settings, build = gradle_file(root, 'settings'), gradle_file(root, 'build')
    settings_text, build_text = settings.read_bytes().decode(), build.read_bytes().decode()
    if re.search(r'["\']:?TeamCodeSim["\']', without_block(settings_text, 'settings')):
        raise WizardError('An unmanaged TeamCodeSim inclusion already exists. Remove the manual integration before using the wizard.')
    if re.search(r'["\']runSimulator["\']', without_block(build_text, 'tasks')):
        raise WizardError('An unmanaged runSimulator task already exists. Remove/rename it first.')
    sdk = sdk_directory(args.sdk)
    if args.copy_sdk and (sdk == root or root in sdk.parents):
        raise WizardError('Cannot vendor an SDK located inside the destination project.')
    kotlin_files = list((root / 'TeamCode/src/main').rglob('*.kt'))
    plugin = kotlin_setup(root, bool(kotlin_files), args.kotlin_version)
    opmodes = args.opmode or discover_opmodes(root)
    for name in opmodes:
        if not re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+', name):
            raise WizardError('Invalid OpMode class name: ' + name)
    plan = Plan(root, args.force)
    destination_sdk = root / '.ftcsim/distribution/sdk' if args.copy_sdk else sdk
    if args.copy_sdk:
        for path in tree_files(sdk):
            plan.put('.ftcsim/distribution/sdk/' + path.relative_to(sdk).as_posix(), path.read_bytes(), managed=True)
    body = SETTINGS_KTS if settings.suffix == '.kts' else SETTINGS_GROOVY
    plan.put(settings.name, block(settings_text, 'settings', body))
    plan.put(build.name, block(build_text, 'tasks', TASK_KTS if build.suffix == '.kts' else TASK_GROOVY))
    local_path = safe_path(root, 'local.properties')
    local = local_path.read_bytes().decode() if local_path.exists() else ''
    local = re.sub(r'^ftcsim\.sdkDir\s*[=:].*(?:\r?\n|$)', '', local, flags=re.M)
    sdk_value = destination_sdk.as_posix().replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')
    plan.put('local.properties', block(local, 'sdk-path', 'ftcsim.sdkDir=' + sdk_value + '\nftcsim.python=' + str(Path(sys.executable).resolve()).replace('\\', '\\\\'), '#'))
    ignore_path = safe_path(root, '.gitignore')
    ignored = ignore_path.read_bytes().decode() if ignore_path.exists() else ''
    plan.put('.gitignore', block(ignored, 'ignore', '.ftcsim/\nlocal.properties', '#'))
    module = MODULE.replace('__KOTLIN_PLUGIN__', plugin).replace('__KOTLIN_SOURCES__', KOTLIN_SOURCES if plugin else '')
    module = module.replace('__OPMODES__', json.dumps(','.join(opmodes)))
    plan.put('TeamCodeSim/build.gradle', module, managed=True)
    plan.put('TeamCodeSim/aar-to-jar.gradle', AAR_TRANSFORM, managed=True)
    plan.put('TeamCodeSim/README.md', PROJECT_README, managed=True)
    extra = safe_path(root, 'TeamCodeSim/extra-dependencies.gradle')
    if not extra.exists():
        plan.put('TeamCodeSim/extra-dependencies.gradle', EXTRA_DEPENDENCIES)
    config = safe_path(root, 'TeamCodeSim/robot.json')
    if args.robot_xml:
        configuration = robot_xml(args.robot_xml.expanduser().resolve())
        plan.put('TeamCodeSim/robot.json', json.dumps(configuration, indent=2) + '\n')
    elif not config.exists():
        plan.put('TeamCodeSim/robot.json', json.dumps({'devices': [], 'note': 'Configure ports in the browser DS before INIT, or rerun with --robot-xml.'}, indent=2) + '\n')
    project_name = re.search(r'rootProject\.name\s*=\s*["\']([^"\']+)', settings_text)
    module_name = (project_name[1] if project_name else root.name) + '.TeamCode'
    for filename, name, task in [('Simulator', 'FTC Simulator', ':TeamCodeSim:run'), ('Backend', 'FTC Simulator Backend', ':TeamCodeSim:startBackend')]:
        plan.put(f'.run/FTCSim_{filename}.run.xml', run_xml(name, task=task), managed=True)
    plan.put('.run/FTCSim_Robot.run.xml', run_xml('FTC Robot', module=module_name), managed=True)
    plan.state(sdk, 'copy' if args.copy_sdk else 'link')
    return plan, opmodes


def add_arguments(result):
    result.add_argument('--project', type=Path, default=Path.cwd(), help='FTC project root; defaults to current directory')
    result.add_argument('--sdk', help='Override the packaged compiled SDK directory')
    result.add_argument('--copy-sdk', action='store_true', help='Copy compiled SDK into the project instead of linking the installation')
    result.add_argument('--opmode', action='append', help='Fully qualified class; repeat to register multiple (otherwise discover top-level OpModes)')
    result.add_argument('--robot-xml', type=Path, help='FTC robot configuration XML to import supported motor/servo mappings')
    result.add_argument('--kotlin-version', help='Required for Kotlin projects without an existing root Kotlin plugin')
    result.add_argument('--dry-run', action='store_true', help='Show changes without writing anything')
    result.add_argument('--yes', '-y', action='store_true', help='Apply without the final interactive prompt')
    result.add_argument('--force', action='store_true', help='Back up and replace edited/unowned generated files; never edit robot sources')
    return result


def run(args):
    try:
        if not args.yes and not args.dry_run and sys.stdin.isatty():
            print('FTC simulator setup. Robot source files will not be edited.')
            if not args.robot_xml:
                selected = input('Robot configuration XML (Enter to configure ports in browser later): ').strip()
                if selected:
                    args.robot_xml = Path(selected)
        plan, opmodes = make_plan(args)
        print('Project:', plan.root)
        print('OpModes:', ', '.join(opmodes) or 'none discovered; SDK built-in demos only')
        print('SDK:', 'copy into project' if args.copy_sdk else 'link packaged SDK')
        print(f'Planned changes: {len(plan.changes)}')
        for change in plan.changes[:25]:
            print('  ' + ('delete ' if change.after is None else 'create ' if change.before is None else 'update ') + change.name)
        if len(plan.changes) > 25:
            print(f'  ... {len(plan.changes) - 25} additional SDK/installer files')
        if not plan.changes:
            print('Already configured; no files changed.')
            return 0
        if args.dry_run:
            print('Dry run: nothing written.')
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                raise WizardError('Noninteractive invocation: use --yes to apply or --dry-run to inspect.')
            if input('Apply these changes? [y/N] ').strip().lower() not in ('y', 'yes'):
                print('Cancelled; no files changed.')
                return 0
        backup = plan.apply()
        print('Configured TeamCodeSim. Backups:', backup)
        print('Sync Gradle in Android Studio. Start FTC Simulator Backend, then FTC Simulator.')
        print('Or use ./gradlew :TeamCodeSim:startBackend and ./gradlew runSimulator in separate terminals.')
        print('Review TeamCodeSim/robot.json before INIT. Unsupported hardware/services still require simulator support.')
        return 0
    except (WizardError, OSError, ValueError) as error:
        console.print(f'Setup failed: {error}', style='red', markup=False)
        return 1



SETTINGS_KTS = (Path(__file__).parent / 'templates/settings_kts.txt').read_text()
SETTINGS_GROOVY = (Path(__file__).parent / 'templates/settings_groovy.txt').read_text()
TASK_KTS = (Path(__file__).parent / 'templates/task_kts.txt').read_text()
TASK_GROOVY = (Path(__file__).parent / 'templates/task_groovy.txt').read_text()
KOTLIN_SOURCES = (Path(__file__).parent / 'templates/kotlin_sources.txt').read_text()
MODULE = (Path(__file__).parent / 'templates/module.txt').read_text()
AAR_TRANSFORM = (Path(__file__).parent / 'templates/aar_transform.txt').read_text()
EXTRA_DEPENDENCIES = (Path(__file__).parent / 'templates/extra_dependencies.txt').read_text()
PROJECT_README = (Path(__file__).parent / 'templates/project_readme.txt').read_text()

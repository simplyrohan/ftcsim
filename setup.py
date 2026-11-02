"""Compile the SDK and static Driver Station for normal and editable wheels."""
import runpy
import shutil
from functools import cache
from pathlib import Path
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.editable_wheel import editable_wheel


@cache
def build_assets():
    runpy.run_path('scripts/build_driver_station.py', run_name='__main__')
    runpy.run_path('scripts/build_sdk.py', run_name='__main__')


class BuildPy(build_py):
    def run(self):
        build_assets()
        if not self.editable_mode:
            package = Path(self.build_lib) / 'ftcsim'
            source = Path(self.get_package_dir('ftcsim')).resolve()
            # Remove stale hashed assets and JARs from incremental builds.
            for name in ('web', 'sdk'):
                target = package / name
                if target.resolve() != source / name and target.is_dir():
                    shutil.rmtree(target)
        super().run()


class EditableWheel(editable_wheel):
    def run(self):
        build_assets()
        super().run()


setup(cmdclass={'build_py': BuildPy, 'editable_wheel': EditableWheel})

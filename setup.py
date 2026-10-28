"""Compile the desktop SDK whenever a wheel (including an editable wheel) is built."""
import runpy
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.editable_wheel import editable_wheel


def build_sdk():
    runpy.run_path('scripts/build_sdk.py', run_name='__main__')


class BuildPy(build_py):
    def run(self):
        build_sdk()
        super().run()


class EditableWheel(editable_wheel):
    def run(self):
        build_sdk()
        super().run()


setup(cmdclass={'build_py': BuildPy, 'editable_wheel': EditableWheel})

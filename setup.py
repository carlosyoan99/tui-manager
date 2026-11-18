#!/usr/bin/env python3
"""
Setup script para TUI Manager
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leer archivo de requisitos
def read_requirements():
    requirements = []
    with open('requirements.txt', 'r') as f:
        in_dev = False
        for line in f:
            line = line.strip()
            if line.startswith('#') and 'Desarrollo' in line:
                in_dev = True  # el resto del archivo es tooling de desarrollo
            if in_dev:
                continue
            if line and not line.startswith('#') and not line.startswith('-'):
                requirements.append(line)
    return requirements

# Leer archivo README
def read_readme():
    readme_file = Path(__file__).parent / 'README.md'
    if readme_file.exists():
        return readme_file.read_text()
    return ""

setup(
    name='tui-manager',
    version='0.3.0a3',
    description='Panel de control portable para la terminal: paquetes, procesos, sistema y temas (Linux, BSD, Termux)',
    author='Carlos Yoan',
    author_email='carlosyoan@local',
    url='https://github.com/carlosyoan/TUI-Manager',
    license='MIT',

    packages=find_packages(exclude=['tests', 'docs', 'config', 'venv']),

    python_requires='>=3.10',

    install_requires=read_requirements(),

    entry_points={
        'console_scripts': [
            'tui-manager=tui_manager.main:main',
        ],
    },

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
    ],

    keywords='tui terminal package manager process monitor linux bsd termux cross-platform',

    long_description=read_readme(),
    long_description_content_type='text/markdown',
)

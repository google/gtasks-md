#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(
    name="gtasks-md",
    version="0.0.1",
    description="A tool to manage Google Tasks using a markdown document.",
    author="Michal Kielbowicz",
    author_email="gtasks-md@kielbowi.cz",
    packages=["app"] + find_packages(),
    entry_points={"console_scripts": ["gtasks-md=app.cli:main"]},
    python_requires=">=3.10",
    include_package_data=True,
    setup_requires=['pytest-runner']
)

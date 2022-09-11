#!/usr/bin/env python3
# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gtasks-md",
    author="Michal Kielbowicz",
    author_email="gtasks-md@kielbowi.cz",
    url="https://github.com/google/gtasks-md",
    description="A tool to manage Google Tasks using a markdown document.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
    install_requires=[
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "pandoc",
        "xdg",
    ],
    entry_points={"console_scripts": ["gtasks-md=app.cli:main"]},
    packages=["app"],
    version="0.0.1",
    license="Apache License 2.0",
)

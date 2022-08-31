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
)

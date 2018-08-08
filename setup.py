#!/usr/bin/python
#
# Copyright 2017 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
from setuptools import setup
import os
import sys
import json
from setuptools.command.develop import develop
from setuptools.command.install import install


def create_default_conf():
    fname = "/etc/ips-regquery/config.json"
    if os.path.isfile(fname):
        return

    defaultData = {
        "priority": 100
    }

    try:
        try:
            os.makedirs(os.path.dirname(fname))
        except OSError as e:
            if e.errno != os.errno.EEXIST:
                raise
            pass

        with open(fname, 'w') as outfile:
            json.dump(defaultData,
                      outfile,
                      sort_keys=True,
                      indent=4,
                      separators=(",", ": "))
    except OSError as e:
        if e.errno != os.errno.EACCES:
            raise
        pass
        # Default config couldn't be created.
        # Code will fallback to hardcoded defaults.
        # This should only happen with un-privileged installs


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        create_default_conf()


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        create_default_conf()


def is_package(path):
    return (
        os.path.isdir(path) and
        os.path.isfile(os.path.join(path, '__init__.py'))
        )


def find_packages(path, base=""):
    """ Find all packages in path """
    packages = {}
    for item in os.listdir(path):
        dir = os.path.join(path, item)
        if is_package(dir):
            if base:
                module_name = "%(base)s.%(item)s" % vars()
            else:
                module_name = item
            packages[module_name] = dir
            packages.update(find_packages(dir, module_name))
    return packages


packages = find_packages(".")
package_names = packages.keys()

# REMEMBER: If this list is updated, please also update stdeb.cfg and the RPM specfile
packages_required = [
    "gevent>=1.2.2",
    "nmoscommon",
    "flask>=0.10.1",
    "systemd>=0.16.1",
    "ws4py>=0.3.4",
    "requests>=0.9.3"
]

setup(name="registryquery",
      version="0.2.6",
      description="nmos query API",
      url='www.nmos.tv',
      author='Peter Brightwell',
      author_email='peter.brightwell@bbc.co.uk',
      license='Apache 2',
      packages=package_names,
      package_dir=packages,
      install_requires=packages_required,
      scripts=[],
      data_files=[
        ('/usr/bin', ['bin/nmosquery'])
      ],
      long_description="Implementation of the service discovery backend.",
      cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
      }
      )

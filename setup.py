# Copyright (c) 2019 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from glob import glob

from setuptools import setup, find_packages
packagedata = True


from gitpy_versioning import get_version

test = ['vcrpy', 'mock', 'pytest']

setup_args = {
    'name':               'steelscript.netprofiler',
    'namespace_packages': ['steelscript'],
    'version':            get_version(),
    'author':             'Riverbed Technology',
    'author_email':       'eng-github@riverbed.com',
    'url':                'http://pythonhosted.org/steelscript',
    'license':            'MIT',
    'description':        'Python module for interacting with Riverbed '
                          'NetProfiler with SteelScript',

    'long_description': '''SteelScript for NetProfiler
===========================

SteelScript is a collection of libraries and scripts in Python and JavaScript
for interacting with Riverbed Technology devices.

For a complete guide to installation, see:

http://pythonhosted.org/steelscript/
    ''',

    'platforms': 'Linux, Mac OS, Windows',

    'classifiers': [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Topic :: System :: Networking',
    ],

    'packages': find_packages(exclude=('gitpy_versioning',)),

    'data_files': (
        ('share/doc/steelscript/docs/netprofiler', glob('docs/*')),
        ('share/doc/steelscript/examples/netprofiler', glob('examples/*')),
        ('share/doc/steelscript/notebooks/netprofiler', glob('notebooks/*')),
    ),

    'install_requires': (
        'steelscript>=2.0',
    ),

    'extras_require': {
        'test': test
    },

    'tests_require': test,

    'python_requires': '>3.5.0',

    'entry_points': {
        'steel.commands': [
            'netprofiler = steelscript.netprofiler.commands'
        ],
        'portal.plugins': [
            'netprofiler = steelscript.netprofiler.appfwk.plugin:NetProfilerPlugin'
        ],
    },
}

if packagedata:
    setup_args['include_package_data'] = True

setup(**setup_args)

Riverbed SteelScript for Cascade NetProfiler
=========================================

This package provides device specific bindings for interacting
with Riverbed Cascade NetProfiler devices as part of the Riverbed
Steelscript for Python.

See [http://github.com/riverbed/steelscript.common](steelscript.common) for
installation instructions.

Quick Start
===========

If you are familiar with installing Python packages, the FlyScript
package leverages the standard setup.py based on setuptools.  You may
want to first setup virtualenv before running setup.  See the
'virtualenv' section in the installation guide.

To get started, you need to complete the following steps:

1. Download the FlyScript package and extract the contents
2. Optionally set up virtualenv
3. Install the FlyScript package using "cd flyscript && python setup.py install"
4. Test it with "python examples/about.py"
5. Read the docs at "docs/html/index.html"
6. Look at the examples in "examples"

Start coding!

How to run tests
================

The suggested way to run tests is through [pytest](http://pytest.org/latest/)
The easiest way to install pytest is through
[python pip](http://www.pip-installer.org/en/latest/installing.html) with:

    pip install pytest testscenarios

This will download and install py.test and the testscenarios packages along
with all of their dependencies.

In order to run the tests you nedd a configuration file in which there are
specified the hosts to run against. The file must look like


    global config

    config = {
       '4.0': [
        ('vshark-xebec', {'host': 'vdorothy10.lab.nbttech.com'})],

       '5.0': [
        ('vshark-latest', {'host':'vdorothy5.lab.nbttech.com'}),
        ('shark-latest', {'host':'oak-mako10.lab.nbttech.com'})

        ],
	'profilerhost': 'tm08-1.lab.nbttech.com'
    }


and should be named `testconfig.py`. The file should be placed in the root
dir of the flyscript package, alongside to the `rvbd` folder.
The Sharks are ordered by API that should be tested. NetShark hosts that are in the 4.0
group will be tested against common calls and specific 4.0 calls. NetShark hosts that
are in the 5.0 group will be tested against common calls and specific 5.0 calls.

To run the tests do:

    py.test

You will see an output like:

    ================================= test session starts ==================================
    platform linux2 -- Python 2.7.4 -- pytest-2.3.2
    collected 76 items

    examples/test_examples.py ..
    rvbd/common/test/test_jsondict.py .........
    rvbd/profiler/test/test_profiler.py ......................
    rvbd/shark/test/test_dpi.py .....
    rvbd/shark/test/test_filters.py .
    rvbd/shark/test/test_settings.py ..................
    rvbd/shark/test/test_shark.py .............................


License
=======

Copyright (c) 2014 Riverbed Technology, Inc.

SteelScript-NetProfiler is licensed under the terms and conditions of the MIT
License accompanying the software ("License").  SteelScript-NetProfiler is
distributed "AS IS" as set forth in the License.

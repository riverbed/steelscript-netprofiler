# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.



from steelscript.common.app import Application
from steelscript.netprofiler.core import NetProfiler


class NetProfilerApp(Application):
    """Simple class to wrap common command line parsing"""
    def __init__(self, *args, **kwargs):
        super(NetProfilerApp, self).__init__(*args, **kwargs)
        self.netprofiler = None

    def parse_args(self):
        super(NetProfilerApp, self).parse_args()

    def add_positional_args(self):
        self.add_positional_arg('host', 'NetProfiler hostname or IP address')

    def add_options(self, parser):
        super(NetProfilerApp, self).add_options(parser)
        self.add_standard_options()

    def setup(self):
        super(NetProfilerApp, self).setup()
        self.netprofiler = NetProfiler(self.options.host,
                                       port=self.options.port,
                                       auth=self.auth)

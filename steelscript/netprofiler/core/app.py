# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


from steelscript.common.app import Application
from steelscript.netprofiler.core import NetProfiler


class NetProfilerApp(Application):
    """Simple class to wrap common command line parsing"""
    def __init__(self, *args, **kwargs):
        super(NetProfilerApp, self).__init__(*args, **kwargs)
        self.optparse.set_usage('%prog NETPROFILER_HOSTNAME <options>')
        self.netprofiler = None

    def parse_args(self):
        super(NetProfilerApp, self).parse_args()
        self.host = self.args[0]

    def setup(self):
        self.netprofiler = NetProfiler(self.host,
                                       port=self.options.port,
                                       auth=self.auth)

    def validate_args(self):
        if len(self.args) < 1:
            self.optparse.error('missing NETPROFILER_HOSTNAME')

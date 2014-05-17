#!/usr/bin/env python

# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.




from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.netprofiler.core.report import TrafficFlowListReport
from steelscript.common.utils import Formatter

import optparse

class NetProfilerReport(NetProfilerApp):

    def add_options(self, parser):
        group = optparse.OptionGroup(parser, "Traffic Flow Options")
        group.add_option('--time0', dest='time0', default=None,
                         help='Start time for report')
        group.add_option('--time1', dest='time1', default=None,
                         help='End time for report')
        group.add_option('-r', '--timerange', dest='timerange', default=None,
                         help='Optional time range in place of t0 and t1')
        group.add_option('-e', '--traffic-expression', dest='trafficexpr', default=None,
                         help='Traffic Expression to query on')
        parser.add_option_group(group)

    def validate_args(self):
        """ Check that either both t0 and t1 are used or timerange
        """
        super(NetProfilerReport, self).validate_args()

        if self.options.timerange and (self.options.time0 or
                                       self.options.time1):
            self.optparse.error('timerange and t0/t1 are mutually exclusive, '
                                'choose only one.')


    def main(self):
        """ Setup query and run report with default column set
        """
        if self.options.timerange:
            timefilter = TimeFilter.parse_range(self.options.timerange)
        else:
            timefilter = TimeFilter(self.options.time0, self.options.time1)
        trafficexpr = TrafficFilter(self.options.trafficexpr)

        columns = [self.netprofiler.columns.key.srv_host_ip,
                   self.netprofiler.columns.key.app_info,
                   self.netprofiler.columns.key.start_time,
                   self.netprofiler.columns.key.end_time,
                   self.netprofiler.columns.value.s2c_total_bytes,
                   self.netprofiler.columns.value.s2c_total_pkts,
                   self.netprofiler.columns.value.response_time,
                   self.netprofiler.columns.value.server_delay]

        report = TrafficFlowListReport(self.netprofiler)
        report.run(columns, timefilter=timefilter, trafficexpr=trafficexpr)
        data = report.get_data()
        report.delete()

        headers = [c.key for c in columns]

        Formatter.print_table(data, headers)


if __name__ == '__main__':
    NetProfilerReport().run()

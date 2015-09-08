#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import optparse

from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.filters import TimeFilter
from steelscript.netprofiler.core.report import \
    TrafficSummaryReport, TrafficTimeSeriesReport
from steelscript.common.datautils import Formatter


class TopPortsTime(NetProfilerApp):

    def add_options(self, parser):
        super(TopPortsTime, self).add_options(parser)

        group = optparse.OptionGroup(parser, "Report Options")
        group.add_option(
            '--timefilter',
            default='last 15 min',
            help=('Time range to analyze (defaults to "last 15 min") '
                  'other valid formats are: "4/21/13 4:00 to 4/21/13 5:00" '
                  'or "16:00:00 to 21:00:04.546"'))

        group.add_option(
            '-N',
            default=10,
            help=('Top N to report on'))

        parser.add_option_group(group)

    def main(self):
        netprof = self.netprofiler

        timefilter = TimeFilter.parse_range(self.options.timefilter)

        # Create and run a traffic summary report of all server ports in use
        report = TrafficSummaryReport(netprof)

        # Run the report
        report.run(
            groupby=netprof.groupbys.port,
            columns=[netprof.columns.key.protoport,
                     netprof.columns.key.protocol,
                     netprof.columns.key.port,
                     netprof.columns.value.avg_bytes],
            sort_col=netprof.columns.value.avg_bytes,
            timefilter=timefilter)

        # Retrieve and print data
        ports_data = report.get_data()[:int(self.options.N)]
        report.delete()

        # Now create a new report using the ports_data
        report = TrafficTimeSeriesReport(netprof)

        # The format the query_columns for 'ports' is:
        #    'ports' = [{'name': 'tcp/80'},
        #               {'name': 'tcp/443'},
        #               {'name': 'icmp/0'}]
        # For most protocols, this works just fine from the report data,
        # but for icmp the result from data is 'icmp/0/0' -- where the two
        # zeros are type and code.  This doesn't work for input to
        # netprofiler, it expects type and code to be smushed into a single
        # 16-bit number (type << 8 | code).
        query_columns = []
        for (protoport, protocol, port, avgbytes) in ports_data:
            if protoport.startswith('icmp'):
                protoport = 'icmp/%s' % (port)

            query_columns.append({'name': protoport})

        # Run the report
        report.run(columns=[netprof.columns.key.time,
                            netprof.columns.value.avg_bytes],
                   resolution='1 min',
                   query_columns_groupby='ports',
                   query_columns=query_columns,
                   timefilter=timefilter)

        # Get the data!
        data = report.get_data()
        Formatter.print_table(
            data, padding=1,
            headers=(['time'] + [q['name'] for q in query_columns]))


if __name__ == "__main__":
    TopPortsTime().run()

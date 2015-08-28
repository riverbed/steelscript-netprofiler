#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.report import WANSummaryReport, WANTimeSeriesReport
from steelscript.netprofiler.core.filters import TimeFilter

import sys
import optparse
import cStringIO as StringIO

# suppress warnings from pandas 0.11
import warnings
warnings.simplefilter(action="ignore", category=FutureWarning)


class WANReportApp(NetProfilerApp):

    def add_options(self, parser):
        super(WANReportApp, self).add_options(parser)
        group = optparse.OptionGroup(parser, "Device List Options")
        group.add_option('--device-address', dest='device_address', default=None,
                         help='IP address for WAN device')
        group.add_option('--device-name', dest='device_name', default=None,
                         help='Text of device name to search for (simple search only,'
                              ' no regular expressions')
        group.add_option('--lan-address', dest='lan_address', default=None,
                         help='LAN interface address')
        group.add_option('--wan-address', dest='wan_address', default=None,
                         help='WAN interface address')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Filter Options")
        group.add_option('--timefilter', dest='timefilter', default='last 1 hour',
                         help='Time range to analyze (defaults to "last 1 hour")')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Report Type Options (choose one)")
        group.add_option('--summary', dest='summary', default=False, action='store_true',
                         help='Generate Summary report of WAN address')
        group.add_option('--time-series', dest='time_series', default=False, action='store_true',
                         help='Generate Time Series report of WAN address')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Output options")
        group.add_option('--inbound', dest='out_inbound', default=False, action='store_true',
                         help='Print inbound statistics')
        group.add_option('--outbound', dest='out_outbound', default=False, action='store_true',
                         help='Print outbound statistics')
        group.add_option('--combined', dest='out_combined', default=False, action='store_true',
                         help='Print combined inbound/outbound statistics')
        group.add_option('--csv', dest='as_csv', default=False, action='store_true',
                         help='Return values in CSV format instead of tabular')

        parser.add_option_group(group)

    def validate_args(self):
        """ Ensure either wan-address or wan-device-name chosen
        """
        super(WANReportApp, self).validate_args()

        if (not self.options.device_address and
                not self.options.device_name and
                not (self.options.lan_address and self.options.wan_address)):
            self.parser.error('Either device-address, device-name or '
                              'both lan-address and wan-address required')
        elif not self.options.summary and not self.options.time_series:
            self.parser.error('Either summary or time_series option required')
        elif not any([self.options.out_inbound,
                      self.options.out_outbound,
                      self.options.out_combined]):
            self.parser.error('Choose at least one output option: '
                              '--inbound, --outbound, --combined')

    def print_data(self, data, header):
        if self.options.as_csv:
            f = StringIO.StringIO()
            data.to_csv(f, header=True)
            print f.getvalue()
        else:
            print header
            print data

    def main(self):
        self.ip_address = None
        self.lan_address = None
        self.wan_address = None
        self.timefilter = TimeFilter.parse_range(self.options.timefilter)

        if self.options.wan_address and self.options.lan_address:
            self.ip_address = self.options.wan_address.split(':')[0]
            self.lan_address = [self.options.lan_address]
            self.wan_address = [self.options.wan_address]
        elif self.options.device_name:
            name = self.options.device_name
            devices = self.netprofiler.api.devices.get_all()
            for d in devices:
                if name.lower() in d['name'].lower():
                    self.ip_address = d['ipaddr']
                    break
            else:
                print 'Device %s cannot be found in NetProfiler device list' % name
                print 'Try specifying the name differently or use an IP address'
                sys.exit(1)
        else:
            self.ip_address = self.options.device_address

        if self.options.summary:
            self.columns = ['device',
                            'avg_bytes',
                            'total_bytes']
            self.groupby = 'dev'
            ReportClass = WANSummaryReport
        else:
            # Time Series report
            self.columns = ['time',
                            'avg_bytes',
                            'total_bytes']
            self.groupby = None
            ReportClass = WANTimeSeriesReport

        with ReportClass(self.netprofiler) as report:
            if not self.lan_address:
                # query for the interfaces
                self.lan_address, self.wan_address = report.get_interfaces(self.ip_address)

            if self.options.out_inbound or self.options.out_combined:
                # inbound
                report.run(self.lan_address, self.wan_address, 'inbound', columns=self.columns,
                           groupby=self.groupby, timefilter=self.timefilter, resolution='auto')
                inbound = report.get_data(as_list=False)

                if self.options.out_inbound:
                    header = 'Inbound traffic:'
                    self.print_data(inbound, header)

            if self.options.out_outbound or self.options.out_combined:
                # outbound
                report.run(self.lan_address, self.wan_address, 'outbound', columns=self.columns,
                           groupby=self.groupby, timefilter=self.timefilter, resolution='auto')
                outbound = report.get_data(as_list=False)

                if self.options.out_outbound:
                    header = 'Outbound traffic:'
                    self.print_data(outbound, header)

            if self.options.out_combined:
                header = 'Combined Inbound/Outbound traffic:'
                total = inbound + outbound
                self.print_data(total, header)


if __name__ == '__main__':
    WANReportApp().run()

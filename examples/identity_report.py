#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.



from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.netprofiler.core.report import (IdentityReport,
                                                 TrafficOverallTimeSeriesReport,
                                                 TrafficSummaryReport)
from steelscript.common.datautils import Formatter
from steelscript.common.timeutils import string_to_datetime

import sys
import imp
import datetime
import optparse
import itertools


AGGREGATION = {'total': lambda x: sum(x),
               'avg'  : lambda x: sum(x) / len(x),
               'peak' : lambda x: max(x),
               'min'  : lambda x: min(x)}

# Columns for Time Series Report
TCOLUMNS = [
    ('time', AGGREGATION['min']),
    ('total_bytes', AGGREGATION['total']),
    ('avg_bytes', AGGREGATION['avg']),
    ('network_rtt', AGGREGATION['peak']),
    ('response_time', AGGREGATION['peak']),
    ('server_delay', AGGREGATION['peak']),
    ('avg_conns_rsts', AGGREGATION['avg']),
    ('avg_pkts_rtx', AGGREGATION['avg']),
    ('avg_rsec_jitter', AGGREGATION['avg']),
    ('avg_vqual_mos', AGGREGATION['min']),
]

# Columns for Traffic Summary Report
SCOLUMNS = [
    ('total_bytes', AGGREGATION['total']),
    ('avg_bytes', AGGREGATION['avg']),
    ('network_rtt', AGGREGATION['peak']),
    ('response_time', AGGREGATION['peak']),
    ('server_delay', AGGREGATION['peak']),
    ('avg_conns_rsts', AGGREGATION['avg']),
    ('avg_pkts_rtx', AGGREGATION['avg']),
    ('avg_rsec_jitter', AGGREGATION['avg']),
    ('avg_vqual_mos', AGGREGATION['min']),
]


def format_time(value):
    """Convenience function to translate timestamp to ISO format"""
    t = datetime.datetime.fromtimestamp(value)
    return t.isoformat(' ')


class IdentityApp(NetProfilerApp):

    def add_options(self, parser):
        super(IdentityApp, self).add_options(parser)
        group = optparse.OptionGroup(parser, 'Identity Report Options')
        group.add_option('-n', '--identity-name', dest='identity_name',
                         help='Login name to use for search')
        group.add_option('-T', '--traffic-filter', dest='trafficexpr', default=None,
                         help='Traffic filter to narrow down IP address '
                              'search space')

        group.add_option('--time0', dest='time0', default=None,
                         help='Start time for report')
        group.add_option('--time1', dest='time1', default=None,
                         help='End time for report')
        group.add_option('-r', '--timerange', dest='timerange', default=None,
                         help='Optional time range in place of t0 and t1')
        group.add_option('-b', '--backsearch', dest='backsearch', default='24',
                         help='Hours to look backwards to find possible identity match '
                              'defaults to the maximum of "24" hours')

        group.add_option('--resolution', default='auto',
                         help='Time resolution to use for report queries, '
                              'defaults to "auto", may be one of the following: '
                              '("1min", "15min", "hour", "6hour", "day")')
        group.add_option('--timeseries-report', dest='timeseries_report', default=False,
                         action='store_true',
                         help='Run time series traffic reports for hosts during found '
                              'login times.')
        group.add_option('--aggregate', dest='aggregate', default=False,
                         action='store_true',
                         help='Set to group timeseries data into single row per timeperiod.')

        group.add_option('--summary-report', dest='summary_report', default=False,
                         action='store_true',
                         help='Run summary reports for hosts during found login times.')

        group.add_option('--groupby-application', dest='groupby_application', default=False,
                         action='store_true',
                         help='Run summary reports for hosts during found login times.')
        group.add_option('--groupby-interface', dest='groupby_interface', default=False,
                         action='store_true',
                         help='Run summary reports for hosts during found login times.')

        group.add_option('--csv', dest='csv', default=False, action='store_true',
                         help='Print results in CSV table.')
        group.add_option('--tsv', dest='tsv', default=False, action='store_true',
                         help='Print results in TSV (tab-separated-values) table.')

        group.add_option('--testfile', dest='testfile', default=None,
                         help='Optional test file with identity events to use in place of '
                              'actual netprofiler queries.')
        group.add_option('--usecache', dest='usecache', default=False, action='store_true',
                         help='Use internal cache to help with large traffic query sets')

        parser.add_option_group(group)

    def validate_args(self):
        """ Check that either both t0 and t1 are used or time range
        """
        super(IdentityApp, self).validate_args()

        if self.options.timerange and (self.options.time0 or
                                       self.options.time1):
            self.parser.error('timerange and t0/t1 are mutually exclusive, '
                              'choose only one.')

        elif (not self.options.timerange and
              not self.options.time0 and
              not self.options.time1):
            self.parser.error('A timerange must be chosen.')

        elif not self.options.identity_name:
            self.parser.error('An identity_name must be chosen.')

        elif int(self.options.backsearch) > 24:
            self.parser.error('Time for back search cannot exceed "24" hours.')

        elif self.options.timeseries_report and self.options.summary_report:
            self.parser.error('Only one report type may be selected at a time.')

    def identity_report(self, timefilter=None, trafficexpr=None, testfile=None):
        """ Run IdentityReport and return data
        """
        identity = self.options.identity_name

        if not testfile:
            # run report against all users
            print 'Running IdentityReport ...'
            report = IdentityReport(self.netprofiler)
            report.run(timefilter=timefilter, trafficexpr=trafficexpr)
            print 'Report complete, gathering data ...'
            data = report.get_data()

            if identity not in (x[1] for x in data):
                print 'Running report farther back to find identity ...'
                delta = datetime.timedelta(hours=int(self.options.backsearch))
                timefilter.start = timefilter.start - delta
                report.run(timefilter=timefilter, trafficexpr=trafficexpr)
                data = report.get_data()

            if not data:
                print "Empty data results."

            legend = report.get_legend()
            report.delete()
        else:
            print 'Reading from testfile %s ...' % testfile
            try:
                f, path, desc = imp.find_module(testfile)
                test = imp.load_module(testfile, f, path, desc)
                data = test.data
                legend = self.netprofiler.get_columns(test.legend)
            except ImportError:
                print 'Error importing test file %s' % testfile
                print 'Ensure it is in the PYTHONPATH, and contains a valid data object.'
                sys.exit(1)
            finally:
                f.close()

        return legend, data

    def traffic_report(self, host, timefilter, report_type):
        """ Generate average statistics for host given `timefilter` time period

            `report_type` is one of ('timeseries', 'summary')
        """
        print 'Running %s report for %s over %s/%s' % (report_type,
                                                       host,
                                                       timefilter.start,
                                                       timefilter.end)

        texpr = TrafficFilter('host %s' % host)

        if report_type == 'timeseries':
            columns = [c[0] for c in TCOLUMNS]
            report = TrafficOverallTimeSeriesReport(self.netprofiler)
            report.run(columns,
                       timefilter=timefilter,
                       trafficexpr=texpr,
                       resolution=self.options.resolution)
        elif report_type == 'summary':
            columns = [c[0] for c in SCOLUMNS]
            report = TrafficSummaryReport(self.netprofiler)

            if self.options.groupby_application:
                columns.insert(0, 'app_name')
                groupby = 'app'
            elif self.options.groupby_interface:
                columns.insert(0, 'interface_alias')
                columns.insert(0, 'interface')
                groupby = 'ifc'
            else:
                groupby = 'hos'

            report.run(groupby,
                       columns,
                       timefilter=timefilter,
                       trafficexpr=texpr,
                       resolution=self.options.resolution)
        else:
            raise RuntimeError('unknown report type: %s' % report_type)

        print 'Report complete, gathering data ...'
        data = report.get_data()
        if not data:
            print "Empty data results."
        elif len(data) == 10000:
            print 'WARNING: data size exceeds max length of 10000 rows'
        legend = report.get_legend()
        report.delete()

        return legend, data

    def analyze_login_data(self, all_data, legend_columns, single_ip=True):
        """ Identify periods user logged into each host

            `single-ip` indicates that a user may only have one IP at a time.
                Logins indicating a different IP address will mean previous
                IP address has been released.
        """
        logins = {}  # scratch lookup table
        current_ip = None  # last ip of user
        activity = []  # sequence of events

        identity = self.options.identity_name

        legend_keys = [c.key for c in legend_columns]

        # all_data contains a time-ordered list of logins for all users
        # the sort order is latest to earliest, so we want to parse this in the
        # reverse order
        for login in all_data[::-1]:
            login = dict(zip(legend_keys, login))

            time = login['time']
            host = login['host_dns'].strip('|')
            user = login['username']

            if single_ip:
                if current_ip and (host == current_ip or user == identity):
                    # ip changes to new user or user gets assigned new ip
                    start = logins.pop(current_ip)
                    duration = time - start
                    activity.append((current_ip, start, time, duration))
                    current_ip = None

                if user == identity:
                    logins[host] = time
                    current_ip = host
            else:
                if host in logins:
                    # new login to existing host
                    start = logins.pop(host)
                    duration = time - start
                    activity.append((host, start, time, duration))
                    current_ip = None

                if user == identity:
                    logins[host] = time
                    current_ip = host

        activity.sort(key=lambda x: x[1])
        legend = ['Host IP', 'Login Time', 'Logout Time', 'Duration']
        return legend, activity

    def generate_traffic(self, activity, legend_keys, report_type):
        """ Generate traffic data during the time the user was logged-in.
        """
        cache = {}
        combined_activity = []
        for event in activity:
            # handle dns names in host along with IP address
            host = event[0].split('|', 1)[0]

            timefilter = TimeFilter(string_to_datetime(event[1]),
                                    string_to_datetime(event[2]))
            # if event occurs in less than a minute, add extra minute to report
            while len(timefilter.profiler_minutes()) == 1:
                timefilter.end += datetime.timedelta(minutes=1)

            # normalize times to minute increments
            mins = timefilter.profiler_minutes()
            tf = TimeFilter(mins[0], mins[-1])

            if self.options.usecache and report_type == 'timeseries':
                # only consider a hit when whole time period is covered
                minutes = tf.profiler_minutes(astimestamp=True)

                if host in cache and all(t in cache[host] for t in minutes):
                    data = [cache[host][t] for t in minutes]
                else:
                    legend, data = self.traffic_report(host, tf, report_type)
                    # store results in cache by host->times->data
                    cache.setdefault(host, {}).update((int(x[0]), x) for x in data)
            else:
                legend, data = self.traffic_report(host, tf, report_type)

            if data:
                if self.options.aggregate and report_type == 'timeseries':
                    # generate running averages over data samples received
                    # first convert empty strings to zeros, then run averages
                    columns = map(lambda c: [0 if x == '' else x for x in c],
                                                                itertools.izip(*data))
                    aggmap = [x[1] for x in TCOLUMNS]
                    aggregates = [aggmap[i](x) for i, x in enumerate(columns)]
                    combined_activity.append(list(event) + aggregates)
                elif report_type == 'timeseries' or report_type == 'summary':
                    # create entry for each element in report
                    for row in data:
                        r = ['--' if x == '' else x for x in row]
                        combined_activity.append(list(event) + r)
                else:
                    raise RuntimeError('unknown report type: %s' % report_type)

            else:
                # populate result with blanks
                combined_activity.append(list(event) + ['--'] * len(legend))

        traffic_legend = [c.key for c in legend]

        legend = legend_keys + traffic_legend
        return legend, combined_activity

    def main(self):
        """ Setup query and run report with default column set
        """
        if self.options.timerange:
            timefilter = TimeFilter.parse_range(self.options.timerange)
        else:
            timefilter = TimeFilter(self.options.time0, self.options.time1)

        if self.options.trafficexpr:
            trafficexpr = TrafficFilter(self.options.trafficexpr)
        else:
            trafficexpr = None

        legend_columns, all_data = self.identity_report(timefilter=timefilter,
                                                        trafficexpr=trafficexpr,
                                                        testfile=self.options.testfile)

        legend, activity = self.analyze_login_data(all_data, legend_columns)

        if activity and self.options.timeseries_report:
            headers, tbl_data = self.generate_traffic(activity, legend, 'timeseries')
        elif activity and self.options.summary_report:
            headers, tbl_data = self.generate_traffic(activity, legend, 'summary')
        else:
            headers = ('Host IP', 'Login Time', 'Logout Time', 'Duration')
            tbl_data = [(x[0], format_time(x[1]), format_time(x[2]), x[3])
                                                                for x in activity]

        if self.options.csv:
            Formatter.print_csv(tbl_data, headers)
        elif self.options.tsv:
            Formatter.print_csv(tbl_data, headers, delim='\t')
        else:
            Formatter.print_table(tbl_data, headers)


if __name__ == '__main__':
    IdentityApp().run()

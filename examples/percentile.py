#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import numpy
import paramiko
import optparse
import matplotlib.pyplot as plt

from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core import *
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter


class PercentileApp(NetProfilerApp):
    def add_options(self, parser):
        super(PercentileApp, self).add_options(parser)

        group = optparse.OptionGroup(parser, 'data processing')
        group.add_option(
            '-b', '--buckettime', default=5, type='int',
            help="Number of minutes data should be bucketed in (default: 5)")
        group.add_option(
            '-e', '--percentile', default=95, type='int',
            help="Percentile to display data at (default: 95)")

        group = optparse.OptionGroup(parser, 'time frame')
        group.add_option('-t', '--timefilter', default="last 5 m",
            help=("Time filter expression in the form \"last x [{m|h|d|w}]\" "
                  "or \"10-30-2012 10:30am to 10-31-2012 10:02am.\" Default: "
                  "last 5 m"))
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, 'traffic filter')
        group.add_option(
            '-r', '--trafficfilter', default="host 10/8",
            help=("Traffic filter expression to use (e.g., \"host 10/8\"). "
                  "When querying hostgroups, you can also enter just the host "
                  "group type (e.g., \"hostgroup ByLocation\")."))
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, 'output')
        group.add_option('--median', action='store_true', default=False,
                         help="Show the median from the data set")
        group.add_option('--min', action='store_true', default=False,
                         help="Show the minimum from the data set")
        group.add_option('--max', action='store_true', default=False,
                         help="Show the maximum from the data set")
        group.add_option(
            '--clean', action='store_true', default=False,
            help="Show only the name and percentile value")

        group.add_option(
            '-o', '--rawdata', action='store_true', default=False,
            help="Additionally display the raw data used to determine the "
                 "percentile values")
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, 'ssh options')
        group.add_option("--sshusername", help="Username for SSH")
        group.add_option("--sshpassword", help="Password for SSH")
        parser.add_option_group(group)



        group = optparse.OptionGroup(parser, 'list groups')
        group.add_option(
            '--listinterfacegroups', action='store_true', default=False,
            help=("List all available interface groups. Separate hierarchies "
                  "with slashes, e.g. ByRegion/North_America. (Requires "
                  "--sshusername and --sshpassword to be defined.)"))
        group.add_option('--listhostgroups', action='store_true', default=False,
                         help=("List all available host groups, organized by "
                               "group type"))
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, 'graph options')
        group.add_option('--graph',
                         help="Save a time series graph in the provided path.")
        group.add_option('--percentileline', action='store_true', default=True,
                         help="Display a line at the chosen percentile")
        group.add_option('--startzero', action='store_true', default=False,
                         help="Start y axis at zero")
        parser.add_option_group(group)

    def validate_args(self):
        super(PercentileApp, self).validate_args()

        if not 1 <= self.options.percentile <= 100:
            self.parser.error("Percentile must be between 1 and 100")

        if (self.options.listinterfacegroups and
            (self.options.sshpassword is None or self.options.sshusername is None)):
            self.parser.error("When using --listinterfacegroups, --sshusername "
                              "and --sshpassword must be provided.")

    def gen_graph(self, rawdata, bucketed_data, percentile):
        percentile_val = numpy.percentile(bucketed_data, percentile)
        endx = len(bucketed_data) * self.options.buckettime

        if self.options.percentileline:
            plt.axhline(percentile_val, color='r',
                        label="{0}% = {1:,.2f} bytes".format(percentile, percentile_val))

        plt.xlim(xmax=endx)
        plt.xlabel("Time (minutes)")
        plt.xticks(rotation="vertical")

        plt.ylabel("Bytes")

        plt.title("NetProfiler Traffic Data: " + self.options.trafficfilter)
        plt.legend()

        plt.plot(xrange(0, endx, self.options.buckettime), bucketed_data,
                 label=self.options.trafficfilter)

        # If --startzero is set, start y axis at zero (naturally). Otherwise
        # keep the min value set by the autoscale feature of plot()
        ymin = 0 if self.options.startzero else plt.ylim()[0]
        # Add a little vertical space for legend
        ymax = int(max(bucketed_data) * 1.2)
        plt.ylim(ymin, ymax)

        plt.savefig(self.options.graph)

    def bucket_data(self, rawdata, buckettime):
        bucketed_data = []
        bucketvals = []
        for i, avg_bytes in enumerate(rawdata):
            bucketvals.append(avg_bytes)
            if i != 0 and (i % buckettime == 0 or i == (len(rawdata) - 1)):
                # Current bucket is full -- save data and start a new empty bucket.
                bucketed_data.append(numpy.average(bucketvals))
                bucketvals = []

        return bucketed_data

    def list_interface_groups(self, host, sshusername, sshpassword):
        # There appears to be no REST API for getting interface groups, so run
        # a command over SSH and pass along the results.
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=sshusername, password=sshpassword)
        stdout = ssh.exec_command("/usr/mazu/bin/mazu-interfacegroups -l")[1]
        print stdout.read()
        ssh.close()

    def list_host_groups(self, profiler):
        for grouptype in profiler.api.host_group_types.get_all():
            print "Group type:", grouptype['name']

            for group in profiler.api.host_group_types.get_all_groups(grouptype['id']):
                print " " + group['name']

    def report_item(self, profiler, timefilter, trafficfilter,
                    buckettime, percentile):
        """ Calculate and display the percentile report for one item
            (host, interface, hostgroup, etc.)"""
        exptype, _, item_id = trafficfilter.filter.partition(" ")

        centricity = ('hos' if exptype == 'hos' else 'int')

        with TrafficOverallTimeSeriesReport(profiler) as report:
            report.run([profiler.columns.value.avg_bytes],
                       timefilter=timefilter,
                       trafficexpr=trafficfilter,
                       centricity=centricity,
                       resolution='1min')
            report.wait_for_complete()
            data = report.get_data()

        rawdata = [avg_bytes for (avg_bytes, ) in data]
        bucketed_data = self.bucket_data(rawdata, buckettime)

        if self.options.clean:
            print "{} {:,.2f}".format(self.options.trafficfilter,
                                      numpy.percentile(bucketed_data, percentile))
        else:
            if self.options.rawdata:
                print "Raw data points:", ", ".join(str(val) for val in rawdata)

            print "Average bytes at percentile {0}: {1:,.2f}".format(
                  self.options.percentile,
                  numpy.percentile(bucketed_data, percentile))

            if self.options.median:
                print ("Median average bytes: "
                       "{0:,.2f}").format(numpy.percentile(bucketed_data, 50))

            if self.options.max or self.options.min:
                print
                if self.options.max:
                    print "Max average bytes: {0:,.2f}".format(max(bucketed_data))
                if self.options.min:
                    print "Min average bytes: {0:,.2f}".format(min(bucketed_data))

        if self.options.graph:
            self.gen_graph(rawdata, bucketed_data, percentile)
            if not self.options.clean:
                print
                print "Graph saved to", self.options.graph

    def main(self):
        if self.options.listinterfacegroups:
            self.list_interface_groups(self.options.host, self.options.sshusername,
                                       self.options.sshpassword)
            return

        if self.options.listhostgroups:
            self.list_host_groups(NetProfiler(self.options.host, auth=self.auth))
            return

        try:
            timefilter = TimeFilter.parse_range(self.options.timefilter)
        except ValueError:
            print "Could not parse time filter expression."
            return

        profiler = NetProfiler(self.options.host, auth=self.auth)

        if not self.options.clean:
            print "Reporting on the period: {}".format(self.options.timefilter)
            print "Using the traffic filter: {}".format(self.options.trafficfilter)
            print "Calculating data at percentile {}".format(self.options.percentile)
            print ("Averaging based on buckets of {} "
                   "minutes").format(self.options.buckettime)
            if self.options.graph:
                print "Saving a graph to {}".format(self.options.graph)
            print

        trafficfilter = TrafficFilter(self.options.trafficfilter)

        self.report_item(profiler, timefilter, trafficfilter,
                         self.options.buckettime, self.options.percentile)

if __name__ == "__main__":
    PercentileApp().run()

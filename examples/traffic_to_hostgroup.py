# !/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from steelscript.netprofiler.core import *
from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter

import pprint
import optparse


class TrafficToHostGroupApp(NetProfilerApp):
    def add_options(self, parser):
        super(TrafficToHostGroupApp, self).add_standard_options()
        group = optparse.OptionGroup(self.parser, "Host Group Parameters")
        group.add_option(
            '-g', '--group', action='store', default=None,
            help='[REQUIRED] type and group to add gathered data to,'
                 ' separated by a :, ex: "ByLocation:SanFrancisco"')
        group.add_option(
            '-t', '--trafficexpr', action='store', default=None,
            help='[REQUIRED] traffic expression, ex: "host 10/8"')
        group.add_option(
            '-f', '--timefilter', action='store', default="last 5m",
            help='time filter for query, ex: "last 5m"')
        group.add_option(
            '-a', '--append', action='store_true', dest='append', default=False,
            help='append rather than replace host group config')
        self.parser.add_option_group(group)

    def validate_args(self):
        super(TrafficToHostGroupApp, self).validate_args()
        if self.options.group is None:
            self.parser.error("Missing required option: GROUP")
        if self.options.trafficexpr is None:
            self.parser.error("Missing required option: TRAFFICEXPR")

    def main(self):
        # Create and run a traffic summary report of all hosts in use
        # and then take that data and send it to a specified host group
        report = TrafficSummaryReport(self.netprofiler)

        # Run the report
        report.run(
            groupby=self.netprofiler.groupbys.host,
            columns=[self.netprofiler.columns.key.host_ip,
                     self.netprofiler.columns.key.group_name],
            sort_col=self.netprofiler.columns.key.group_name,
            timefilter=TimeFilter.parse_range(self.options.timefilter),
            trafficexpr=TrafficFilter(self.options.trafficexpr)
        )

        # Store the report's data
        data = report.get_data()
        # Grab the type_name and group_name from options.group
        (type_name, group_name) = self.options.group.split(':', 1)
        # Create an array to store the new config data
        new_config_entries = []

        # Using data from the report, put it in config-readable format.
        for i in range(len(data)):
            new_config_entries.append({'cidr': data[i][0] + '/32',
                                       'name': group_name})
        # Make sure that if there were no entries returned,
        # we don't overwrite the old data
        if len(new_config_entries) == 0:
            print('ERROR: Report returned zero hosts for supplied parameters')
            return

        # Get the ID of the host type specified by name
        host_types = self.netprofiler.api.host_group_types.get_all()
        target_type_id = -1
        for i, host_type in enumerate(host_types):
            if type_name == host_type['name']:
                target_type_id = host_type['id']
                break
        # If target_type_id is still -1, then we didn't find that host
        if target_type_id == -1:
            print('ERROR: Host Group Type: "' + type_name + '" was not found.')
            return

        # Get the current config from the target host group
        config = self.netprofiler.api.host_group_types.get_config(target_type_id)
        old_config_size = len(config)
        # If the append flag is not true,
        # remove all entries in config matching group_name
        if self.options.append is False:
            config = filter(lambda a: a['name'] != group_name, config)

        config.extend(new_config_entries)
        new_config_size = len(config)
        self.netprofiler.api.host_group_types.set_config(target_type_id, config)
        print("Successfully updated type: " + type_name +
              ", group: " + group_name)
        print("The old config had " + str(old_config_size) +
              " elements. It now has " + str(new_config_size) + " elements.\n")


TrafficToHostGroupApp().run()

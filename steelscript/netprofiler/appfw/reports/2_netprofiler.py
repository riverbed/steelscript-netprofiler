# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from steelscript.appfw.core.apps.report.models import Report
import steelscript.appfw.core.apps.report.modules.yui3 as yui3

from steelscript.netprofiler.appfw.datasources.netprofiler import (NetProfilerTimeseriesTable,
                                                             NetProfilerGroupbyTable)
#
# NetProfiler report
#

report = Report.create("NetProfiler", position=2)

report.add_section()

# Define a Overall TimeSeries showing Avg Bytes/s
p = NetProfilerTimeseriesTable.create('ts-overall', duration=60, resolution="1min")

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Overall Traffic", width=12)

# Define a TimeSeries showing Avg Bytes/s for tcp/80
p = NetProfilerTimeseriesTable.create('ts-tcp80', duration=60,
                                   filterexpr='tcp/80', cacheable=False)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')
p.add_column('avg_bytes_rtx', 'Avg Retrans Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Bandwidth for tcp/80",
                  altaxis=['avg_bytes_rtx'])

# Define a TimeSeries showing Avg Bytes/s for tcp/443
p = NetProfilerTimeseriesTable.create('ts-tcp443', duration=60, filterexpr='tcp/443')

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')
p.add_column('avg_bytes_rtx', 'Avg Retrans Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Bandwidth for tcp/443")

# Define a Pie Chart for locations
p = NetProfilerGroupbyTable.create('location-bytes', groupby='host_group', duration=60)

p.add_column('group_name', 'Group Name', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s', issortcol=True)

report.add_widget(yui3.PieWidget, p, "Locations by Bytes")

# Define a Table
p = NetProfilerGroupbyTable.create('location-resptime', groupby='host_group', duration=60)

p.add_column('group_name', 'Group Name', iskey=True)
p.add_column('response_time', 'Response Time', units='ms', issortcol=True)

report.add_widget(yui3.BarWidget, p, "Locations by Response Time")

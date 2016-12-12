# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import steelscript.appfwk.apps.report.modules.c3 as c3
from steelscript.appfwk.apps.report.models import Report

from steelscript.netprofiler.appfwk.datasources.netprofiler import \
    NetProfilerTable, NetProfilerTrafficTimeSeriesTable

#
# NetProfiler report
#

report = Report.create("NetProfiler Top Ports/Apps over Time", position=10)
report.add_section()

# Need a "base" column for the top-n report that defines the metric
# to be queried for.  This table is never actually run, only the column
# parameters are used.
base = NetProfilerTable.create('ports-time-base')
base.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

# Create a top 5 report, groupby port
p = NetProfilerTrafficTimeSeriesTable.create(
    'ports-time', base=base, groupby='port', top_n=5)
p.add_column('time', 'Time', datatype='time', iskey=True)

report.add_widget(c3.TimeSeriesWidget, p, "Ports over time",
                  width=6, stacked=True)

# Similar to above, but include others
p = NetProfilerTrafficTimeSeriesTable.create(
    'ports-time-other', base=base, groupby='port',
    include_other=True, top_n=5)

p.add_column('time', 'Time', datatype='time', iskey=True)
report.add_widget(c3.TimeSeriesWidget, p, "Ports over time w/ other",
                  width=6, stacked=True)

# Two more widgets, groupby application
p = NetProfilerTrafficTimeSeriesTable.create(
    'applications-time', base=base, groupby='application', top_n=5)

p.add_column('time', 'Time', datatype='time', iskey=True)
report.add_widget(c3.TimeSeriesWidget, p, "Applications over time",
                  width=6, stacked=True)

p = NetProfilerTrafficTimeSeriesTable.create(
    'applications-time-other', base=base, groupby='application',
    include_other=True, top_n=5)

p.add_column('time', 'Time', datatype='time', iskey=True)
report.add_widget(c3.TimeSeriesWidget, p, "Applications over time w/ other",
                  width=6, stacked=True)

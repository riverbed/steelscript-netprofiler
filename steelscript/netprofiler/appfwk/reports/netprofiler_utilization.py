# Copyright (c) 2019 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import steelscript.appfwk.apps.report.modules.c3 as c3
import steelscript.appfwk.apps.report.modules.tables as tables
from steelscript.appfwk.apps.report.models import Report
from steelscript.netprofiler.appfwk.datasources.netprofiler import (
    NetProfilerTimeSeriesTable,
    NetProfilerGroupbyTable)
#
# NetProfiler report
#

report = Report.create("NetProfiler Utilization", position=10)

report.add_section()

# Define a Overall TimeSeries showing Avg Bytes/s
p = NetProfilerTimeSeriesTable.create('opt-overall', duration=60,
                                      interface=True,
                                      resolution="1min")

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_avg_util', 'In Avg Util %', units='pct')
p.add_column('out_avg_util', 'Out Avg Util %', units='pct')
p.add_column('50-line', '50% Util', synthetic=True, compute_expression='50')
p.add_column('70-line', '70% Util', synthetic=True, compute_expression='70')

report.add_widget(c3.TimeSeriesWidget, p, "Overall Utilization", width=12)


# Define a Pie Chart for locations
p = NetProfilerGroupbyTable.create('util-table', groupby='interface',
                                   duration=60)

p.add_column('interface', 'Interface', datatype='string', iskey=True)
p.add_column('in_avg_util', 'In Avg Util %', units='pct')
p.add_column('out_avg_util', 'Out Avg Util %', units='pct')
p.add_column('in_peak_util', 'In Peak Util %', units='pct')
p.add_column('out_peak_util', 'Out Peak Util %', units='pct')

report.add_widget(tables.TableWidget, p, "Interface Utilization", width=12)

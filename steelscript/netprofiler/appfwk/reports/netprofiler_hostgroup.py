# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.yui3 as yui3

from steelscript.netprofiler.appfwk.datasources.netprofiler import \
    NetProfilerTimeSeriesTable, NetProfilerGroupbyTable, \
    add_netprofiler_hostgroup_field
#
# NetProfiler report
#

report = Report.create("NetProfiler HostGroup Report - ByLocation",
                       position=10,
                       field_order=['netprofiler_device', 'endtime',
                                    'duration', 'resolution', 'hostgroup',
                                    'netprofiler_filterexpr'])

section = report.add_section()

add_netprofiler_hostgroup_field(report, section, 'ByLocation')

# Define a Overall TimeSeries showing Avg Bytes/s
p = NetProfilerTimeSeriesTable.create('ts-overall',
                                      duration=60, resolution="1min")

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Overall Traffic", width=12)

# Define a Pie Chart for top ports
p = NetProfilerGroupbyTable.create('ports-bytes',
                                   groupby='port_group', duration=60)

p.add_column('portgroup', 'Port Group', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s', sortdesc=True)

report.add_widget(yui3.PieWidget, p, "Port Groups by Avg Bytes")

# Define a Bar Chart for application ports
p = NetProfilerGroupbyTable.create('application-bytes',
                                   groupby='application_port', duration=60)

p.add_column('protoport_name', 'Application Port', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s', sortdesc=True)
report.add_widget(yui3.BarWidget, p, "Application Ports by Avg Bytes")

# Define a TimeSeries showing Avg Bytes/s for tcp/80
p = NetProfilerTimeSeriesTable.create('ts-tcp80', duration=60,
                                      filterexpr='tcp/80', cacheable=False)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')
p.add_column('avg_bytes_rtx', 'Avg Retrans Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Bandwidth for tcp/80",
                  altaxis=['avg_bytes_rtx'])

# Define a TimeSeries showing Avg Bytes/s for tcp/443
p = NetProfilerTimeSeriesTable.create('ts-tcp443',
                                      duration=60, filterexpr='tcp/443')

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')
p.add_column('avg_bytes_rtx', 'Avg Retrans Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Bandwidth for tcp/443")

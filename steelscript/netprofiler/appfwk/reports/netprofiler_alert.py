# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.yui3 as yui3

from steelscript.netprofiler.appfwk.datasources.netprofiler import \
    NetProfilerTimeSeriesTable, NetProfilerGroupbyTable

# Trigger related imports
from steelscript.appfwk.apps.alerting.models import create_trigger
import netprofiler_triggers

#
# Description
#
description = """
<div style="width:500px">
<p>This example report demonstrates usage of the alerting functionality.

<p>The report gets defined as usual, with tables for datasources and widgets
for display of the data.  Separately, we define a set of trigger functions
that will analyze the results of the table before it gets displayed.  These
triggers are attachd to the table using the ``create_trigger`` function.

<p>If the trigger evaluates to True, the results can be forwarded to a variety
of ``Destinations`` using a ``Sender`` class.  Multiple ``Destinations``
can be added to a single trigger.
</div>
"""

report = Report.create("NetProfiler - Alert Example",
                       description=description,
                       position=10)
report.add_section()

# Define a Overall TimeSeries showing Avg Bytes/s
p = NetProfilerTimeSeriesTable.create('ts-overall', duration=60, resolution="1min")

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Overall Traffic", width=6)

# Add a trigger to evaluate if traffic exceeds a certain threshold
a = create_trigger(source=p,
                   trigger_func=netprofiler_triggers.local_spike,
                   params={'column': 'avg_bytes',
                           'std': 2})
a.add_destination(
    'LoggingSender',
    options={'level': 'info'},
    template='Logging Local Spike: time - {time}, value - {avg_bytes}'
)

# Define a Table for Response Times
p = NetProfilerGroupbyTable.create('location-resptime', groupby='host_group', duration=60)

p.add_column('group_name', 'Group Name', iskey=True)
p.add_column('response_time', 'Response Time', units='ms', sortdesc=True)

report.add_widget(yui3.BarWidget, p, "Locations by Response Time")

# Add a trigger to evaluate if response time exceeds a certain threshold
a = create_trigger(source=p,
                   trigger_func=netprofiler_triggers.simple_trigger,
                   params={'column': 'response_time',
                           'value': 0.3})
a.add_destination(
    'LoggingSender',
    options={'level': 'info'},
    template='Logging Response Time Exceeded Threshold'
)

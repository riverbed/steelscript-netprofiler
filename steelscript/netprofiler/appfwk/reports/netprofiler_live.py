# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report

from steelscript.netprofiler.appfwk.datasources.netprofiler_live import \
    NetProfilerLiveConfigTable

import steelscript.appfwk.apps.report.modules.yui3 as yui3

report = Report.create("NetProfiler Live Templates")
report.add_section()

p = NetProfilerLiveConfigTable.create('live-templates')

p.add_column('widget_id', 'Widget ID', datatype='integer', iskey=True)
p.add_column('title', 'Title', datatype='string')
p.add_column('widget_type', 'Type', datatype='string')
p.add_column('visualization', 'Visualization', datatype='string')
p.add_column('datasource', 'Data Source', datatype='string')

report.add_widget(yui3.TableWidget, p, 'Widgets Configuration', width=12)

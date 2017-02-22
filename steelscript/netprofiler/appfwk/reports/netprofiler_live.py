# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report

from steelscript.netprofiler.appfwk.datasources.netprofiler_live import \
    NetProfilerLiveConfigTable

import steelscript.appfwk.apps.report.modules.tables as tables

report = Report.create("NetProfiler Live Templates")
report.add_section()

p = NetProfilerLiveConfigTable.create('live-templates')

report.add_widget(tables.TableWidget, p, 'Widgets Configuration', width=12,
                  height=0, searching=True)

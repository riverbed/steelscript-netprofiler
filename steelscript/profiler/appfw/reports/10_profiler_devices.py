# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from steelscript.appfw.core.apps.report.models import Report
import steelscript.appfw.core.apps.report.modules.yui3 as yui3

from steelscript.profiler.appfw.datasources.profiler_devices import ProfilerDeviceTable

report = Report.create("Profiler Device List", position=10)

report.add_section()

#
# Device Table

p = ProfilerDeviceTable.create('devtable')
p.add_column('ipaddr', 'Device IP', iskey=True, datatype="string")
p.add_column('name', 'Device Name', datatype="string")
p.add_column('type', 'Flow Type', datatype="string")
p.add_column('version', 'Flow Version', datatype="string")

report.add_widget(yui3.TableWidget, p, "Device List", height=300, width=12)

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.tables as tables
from steelscript.netprofiler.appfwk.datasources.netprofiler_devices import \
    NetProfilerDeviceTable

report = Report.create("NetProfiler Device List", position=10)

report.add_section()

#
# Device Table

p = NetProfilerDeviceTable.create('devtable')
p.add_column('ipaddr', 'Device IP', iskey=True, datatype="string")
p.add_column('name', 'Device Name', datatype="string", sortasc=True)
p.add_column('type', 'Flow Type', datatype="string")
p.add_column('version', 'Flow Version', datatype="string")

report.add_widget(tables.TableWidget, p, "Device List", height=300, width=12)

#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.services import ServiceLocationReport
from steelscript.netprofiler.core.filters import TimeFilter

import pprint

app = NetProfilerApp()
app.run()

# Create and run a traffic summary report of all server ports in use
# by hosts in 10/8
report = ServiceLocationReport(app.netprofiler)

# Run the report
report.run(
    timefilter=TimeFilter.parse_range("last 1h")
    )

# Retrieve and print data
data = report.get_data()
printer = pprint.PrettyPrinter(2)
printer.pprint(data[:20])

#!/usr/bin/env python

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.



from steelscript.profiler import *
from steelscript.profiler.app import ProfilerApp
from steelscript.profiler.filters import TimeFilter, TrafficFilter

import pprint

def main(app):
    # Create and run a traffic summary report of all server ports in use
    # by hosts in 10/8
    report = TrafficSummaryReport(app.profiler)

    # Run the report
    report.run(
        groupby = app.profiler.groupbys.port,
        columns = [app.profiler.columns.key.protoport,
                   app.profiler.columns.key.protoport_name,
                   app.profiler.columns.value.avg_bytes,
                   app.profiler.columns.value.network_rtt],
        sort_col = app.profiler.columns.value.avg_bytes,
        timefilter = TimeFilter.parse_range("last 15 m"),
        trafficexpr = TrafficFilter("host 10/8")
        )
    
    # Retrieve and print data
    data = report.get_data()
    printer = pprint.PrettyPrinter(2)
    printer.pprint(data[:20])


if __name__ == '__main__':
    ProfilerApp(main).run()

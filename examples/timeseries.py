#!/usr/bin/env python

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.



from steelscript.profiler.core import *
from steelscript.profiler.core.app import ProfilerApp
from steelscript.profiler.core.filters import TimeFilter, TrafficFilter

import pprint

def main(app):
    # Create and run a traffic summary report of all server ports in use
    # by hosts in 10/8
    report = TrafficOverallTimeSeriesReport(app.profiler)

    # Run the report
    report.run(
        columns = [app.profiler.columns.key.time,
                   app.profiler.columns.value.avg_bytes,
                   app.profiler.columns.value.network_rtt],
        timefilter = TimeFilter.parse_range("last 15 m"),
        trafficexpr = TrafficFilter("host 10/8")
    )

    # Retrieve and print data
    data = report.get_data()
    printer = pprint.PrettyPrinter(2)
    printer.pprint(data)


if __name__ == '__main__':
    ProfilerApp(main).run()

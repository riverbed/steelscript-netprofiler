#!/usr/bin/env python

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import sys
import pprint

import steelscript
from steelscript.profiler.core import Profiler

from steelscript.common.service import UserAuth
from steelscript.profiler.core.filters import TimeFilter
from steelscript.profiler.core.report import TrafficSummaryReport

# connection information
username = '<username>'
password = '<password>'
host = '<profiler.ip.address>'

if (username == '<username>' or
        password == '<password>' or
        host == '<profiler.ip.address>'):
    print "Update the username, password, and profiler host values before running this script."
    sys.exit(0)

auth = UserAuth(username, password)

p = Profiler(host, auth=auth)
report = TrafficSummaryReport(p)

columns = [p.columns.key.host_ip,
           p.columns.value.avg_bytes,
           p.columns.value.network_rtt]
sort_column = p.columns.value.avg_bytes
timefilter = TimeFilter.parse_range("last 15 m")

report.run('hos', columns, timefilter=timefilter, sort_col=sort_column)
data = report.get_data()
legend = report.get_legend()
report.delete()

pprint.pprint(data[:10])

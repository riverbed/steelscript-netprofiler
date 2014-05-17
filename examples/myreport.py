#!/usr/bin/env python

# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.



import sys
import pprint

import steelscript
from steelscript.netprofiler.core import NetProfiler

from steelscript.common.service import UserAuth
from steelscript.netprofiler.core.filters import TimeFilter
from steelscript.netprofiler.core.report import TrafficSummaryReport

# connection information
username = '<username>'
password = '<password>'
host = '<netprofiler.ip.address>'

if (username == '<username>' or
        password == '<password>' or
        host == '<netprofiler.ip.address>'):
    print "Update the username, password, and netprofiler host values before running this script."
    sys.exit(0)

auth = UserAuth(username, password)

p = NetProfiler(host, auth=auth)
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

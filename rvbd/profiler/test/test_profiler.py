# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from rvbd.profiler import Profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter
from rvbd.common.service import UserAuth
from rvbd.common.exceptions import RvbdException
from rvbd.profiler.report import (WANSummaryReport, WANTimeSeriesReport, TrafficSummaryReport,
                                  TrafficOverallTimeSeriesReport, TrafficFlowListReport,
                                  IdentityReport)

import unittest
import logging
import datetime

try:
    from testconfig import config
except ImportError:
    if __name__ != '__main__':
        raise
    config = {}

# XXX we try to use unittest.SkipTest() in setUp() below but it
# isn't supported by python 2.6.  this simulates the same thing...
# another 2.6 hack
if 'profilerhost' not in config:
    __test__ = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)-5.5s] %(msg)s")


def create_profiler():
    """ Create Profiler instance given configuration data
    """
    if 'profilerhost' not in config:
        raise unittest.SkipTest('no profiler hostname provided')
    try:
        username = config['username']
    except KeyError:
        username = 'admin'
    try:
        password = config['password']
    except KeyError:
        password = 'admin'
    auth = UserAuth(username, password)
    return Profiler(config['profilerhost'], auth=auth)


class ProfilerTests(unittest.TestCase):
    def setUp(self):
        self.profiler = create_profiler()
        y = datetime.datetime.now() - datetime.timedelta(days=1)
        yesterday_at_4 = datetime.datetime(y.year, y.month, y.day, hour=16, minute=0, microsecond=1)
        yesterday_at_5 = datetime.datetime(y.year, y.month, y.day, hour=17, minute=0, microsecond=1)
        self.yesterday = TimeFilter(yesterday_at_4, yesterday_at_5)

    def test_groupby_structure(self):
        self.assertTrue('port' in self.profiler.groupbys)
        self.assertEqual(self.profiler.groupbys.port, 'por')

    def test_columns_structure(self):
        self.assertEqual(self.profiler.columns.key.host_ip, 'host_ip')
        dir(self.profiler.columns.key)
        self.assertEqual(self.profiler.columns.key.host_ip.id, 5)

    def test_search_columns(self):
        all_columns = self.profiler.search_columns()
        groupby_hos = self.profiler.search_columns(groupbys=['hos'])
        centricities_and_groupby = self.profiler.search_columns(centricities=['hos'],
                                                                groupbys=['tim'])
        assert len(all_columns) > 0
        assert len(groupby_hos) > 0
        assert len(centricities_and_groupby) > 0
        assert len(all_columns) != len(groupby_hos)
        assert len(all_columns) != len(centricities_and_groupby)
        assert len(groupby_hos) != len(centricities_and_groupby)
        logger.debug("Retrieved columns for groupby 'hos': %s" % groupby_hos)

    def test_get_columns(self):
        names = ['time', 'host_ip', 'network_rtt']
        cols = self.profiler.get_columns(names)
        self.assertEqual(len(cols), 3)
        self.assertEqual(cols[0].id, 98)
        self.assertEqual(cols[1].id, 5)
        self.assertEqual(cols[2].id, 280)
        self.assertRaises(RvbdException, self.profiler.get_columns, ['noexist'])
        # test __cmp__ method on Column object
        self.assertTrue(self.profiler.columns.key.time >
                        self.profiler.columns.key.host_ip)

    def test_get_columns_by_ids(self):
        ids = [98, 5, 280]
        cols = self.profiler.get_columns_by_ids(ids)
        self.assertTrue(len(cols) == 3)
        keys = [c.key for c in cols]
        self.assertTrue('time' in keys)
        self.assertTrue('host_ip' in keys)
        self.assertTrue('network_rtt' in keys)

    def test_logout(self):
        pass

    def test_timefilter(self):
        tfilter = TimeFilter.parse_range('9:01:36 to 10:04:39')

        testtime = tfilter.start.replace(minute=33, second=59)
        self.assertTrue(tfilter.compare_time(testtime))
        testtime = tfilter.end.replace(minute=44)
        self.assertFalse(tfilter.compare_time(testtime))

        minutes = tfilter.profiler_minutes()
        self.assertEqual(len(minutes), 64)
        minutes = tfilter.profiler_minutes(astimestamp=True)
        self.assertEqual(len(minutes), 64)
        minutes = tfilter.profiler_minutes(aslocal=True)
        self.assertEqual(len(minutes), 64)

        tfilter = TimeFilter.parse_range('9:01:36 to 9:02:33')
        minutes = tfilter.profiler_minutes()
        self.assertEqual(len(minutes), 1)

    def test_traffic_summary_report(self):
        groupby = self.profiler.groupbys.host
        columns = [self.profiler.columns.key.host_ip,
                   self.profiler.columns.value.avg_bytes,
                   self.profiler.columns.value.avg_pkts]
        sort_col = self.profiler.columns.value.avg_bytes
        timerange = TimeFilter.parse_range("last 1 h")
        trafficexpr = TrafficFilter("host 10/8")

        with TrafficSummaryReport(self.profiler) as rep:
            rep.run(groupby, columns,
                    sort_col, timerange,
                    trafficexpr)
            legend = rep.get_legend()
            self.assertEqual(len(legend), 3)
            legend = rep.get_legend(columns=[self.profiler.columns.key.host_ip,
                                             self.profiler.columns.value.avg_bytes])
            self.assertEqual(len(legend), 2)
            self.assertEqual(legend[0].key, 'host_ip')
            self.assertEqual(legend[1].key, 'avg_bytes')

            data = rep.get_data()
            if data:
                self.assertEqual(len(data[0]), 3)

            #check that data is refetched from cache
            data = rep.get_data()

            data = rep.get_data(columns=[self.profiler.columns.key.host_ip,
                                         self.profiler.columns.value.avg_bytes])
            if data:
                self.assertEqual(len(data[0]), 2)

    def test_traffic_overall_time_series_report(self):

        columns = [self.profiler.columns.key.time,
                   self.profiler.columns.value.avg_bytes,
                   self.profiler.columns.value.avg_pkts]
        
        timerange = TimeFilter.parse_range("last 1 h")
        trafficexpr = TrafficFilter("host 10/8")
        resolution = "15min"
        report = TrafficOverallTimeSeriesReport(self.profiler)
        report.run(columns, timerange, trafficexpr, resolution=resolution)

        legend = report.get_legend()
        keys = [c.key for c in legend]

        data = report.get_data()

        for item in data:
            d = dict(zip(keys, item))
            # resolution assumes 15-minute responses
            self.assertTrue(timerange.compare_time(d['time'], resolution=15*60))
        report.delete()

    def test_traffic_flow_list_report(self):
        columns = [self.profiler.columns.key.srv_host_ip,
                   self.profiler.columns.key.app_info,
                   self.profiler.columns.key.start_time,
                   self.profiler.columns.key.end_time,
                   self.profiler.columns.value.s2c_total_bytes,
                   self.profiler.columns.value.s2c_total_pkts,
                   self.profiler.columns.value.response_time,
                   self.profiler.columns.value.server_delay]
        timerange = TimeFilter.parse_range("last 1 h")
        trafficexpr = TrafficFilter("host 10/8")

        with TrafficFlowListReport(self.profiler) as report:
            report.run(columns, timefilter=timerange, trafficexpr=trafficexpr)

            legend = report.get_legend()
            keys = [c.key for c in legend]
            self.assertTrue('app_info' in keys)

            data = report.get_data()
            if data:
                self.assertEqual(len(data[0]), 8)

    def test_identity_report(self):
        timerange = TimeFilter.parse_range('last 30 m')

        with IdentityReport(self.profiler) as report:
            report.run(timefilter=timerange)
            legend = report.get_legend()
            data = report.get_data()
            keys = [c.key for c in legend]
            self.assertTrue('time' in keys)
            self.assertTrue('username' in keys)
            if data:
                self.assertEqual(len(data[0]), 9)

    def test_unsupported_column(self):
        groupby = self.profiler.groupbys.port

        # host_ip shouldn't be included as part of 'port' groupby
        columns = [self.profiler.columns.key.host_ip,
                   self.profiler.columns.value.avg_bytes,
                   self.profiler.columns.value.avg_pkts]
        sort_col = self.profiler.columns.value.avg_bytes

        timerange = TimeFilter.parse_range("last 1 h")
        trafficexpr = TrafficFilter("host 10/8")

        report = TrafficSummaryReport(self.profiler)
        kwds = dict(groupby=groupby,
                    columns=columns,
                    sort_col=sort_col,
                    timefilter=timerange,
                    trafficexpr=trafficexpr)
        self.assertRaises(RvbdException, report.run, None, kwds)

    def test_resolution(self):
        groupby = self.profiler.groupbys.host
        columns = [self.profiler.columns.key.host_ip,
                   self.profiler.columns.value.avg_bytes,
                   self.profiler.columns.value.avg_pkts]
        sort_col = self.profiler.columns.value.avg_bytes
        trafficexpr = TrafficFilter("host 10/8")
        resolutions = [["1min", "last 5 min"],
                       ["15min", "last 1 hour"],
                       ["hour", "last 4 hours"],
                       ["6hour", "last 1 day"],
                       ["day", "last 1 week"]
                       #"week",
                       #"month"
                       #Commented values blow up with a 
                       #E       RvbdHTTPException: 400 Unknown time resolution.
                       ]
        for (resolution, duration) in resolutions:
            timerange = TimeFilter.parse_range(duration)
            with TrafficSummaryReport(self.profiler) as rep:
                rep.run(groupby, columns,
                        sort_col, timerange,
                        trafficexpr, resolution=resolution)

    def test_area(self):
        self.assertEqual(self.profiler.areas.wan, 'wan')
        self.assertEqual(self.profiler.areas.lan, 'lan')
        self.assertEqual(self.profiler.areas.vxlan_tenant, 'vxlan_tenant')
        self.assertEqual(self.profiler.areas.vxlan_tunnel, 'vxlan_tunnel')
        self.assertEqual(self.profiler.areas.vxlan, 'vxlan')

        # do we really need this bi-directional support?
        self.assertEqual(self.profiler.areas.wan, 'wan')
        self.assertEqual(self.profiler.areas.lan, 'lan')
        self.assertEqual(self.profiler.areas.tnt, 'tnt')
        self.assertEqual(self.profiler.areas.prd, 'prd')
        self.assertEqual(self.profiler.areas.vxl, 'vxl')

    def test_report_with_area(self):
        groupby = self.profiler.groupbys.host
        columns = [self.profiler.columns.key.host_ip,
                   self.profiler.columns.value.avg_bytes,
                   self.profiler.columns.value.avg_pkts]
        sort_col = self.profiler.columns.value.avg_bytes
        timerange = TimeFilter.parse_range("last 1 h")
        trafficexpr = TrafficFilter("host 10/8")
        area = self.profiler.areas.vxlan_tenant
        with TrafficSummaryReport(self.profiler) as rep:
            rep.run(groupby, columns,
                    sort_col, timerange,
                    trafficexpr, area=area)

    def test_wan_time_series_report(self):
        # WAN reports depend on pandas module, so skip if we don't have it
        try:
            import pandas
        except ImportError:
            return

        # we don't have a way to find WAN interfaces yet, so this test is
        # dependent on a profiler running the demo traffic program
        # if we can't find the 'Austin' interface, just end test
        ip_address = None
        devices = self.profiler.api.devices.get_all()
        for d in devices:
            if 'sh-austin' in d['name'].lower():
                ip_address = d['ipaddr']
        if not ip_address:
            return

        columns = ['time',
                   'avg_bytes',
                   'total_bytes']
        self.groupby = None

        with WANTimeSeriesReport(self.profiler) as report:
            lan_address, wan_address = report.get_interfaces(ip_address)
            self.assertTrue(lan_address)
            self.assertTrue(wan_address)

            report.run(lan_address, wan_address, 'inbound', columns=columns,
                       timefilter=self.yesterday, resolution='1min')
            inbound = report.get_data(as_list=False)
            self.assertEqual(inbound.shape, (60,4))
            self.assertTrue(all(inbound.LAN_avg_bytes > inbound.WAN_avg_bytes))

            report.run(lan_address, wan_address, 'outbound', columns=columns,
                       timefilter=self.yesterday, resolution='1min')
            outbound = report.get_data(as_list=False)
            self.assertEqual(outbound.shape, (60,4))
            self.assertTrue(all(outbound.LAN_avg_bytes > outbound.WAN_avg_bytes))

    def test_wan_time_summary_report(self):
        # WAN reports depend on pandas module, so skip if we don't have it
        try:
            import pandas
        except ImportError:
            return

        # we don't have a way to find WAN interfaces yet, so this test is
        # dependent on a profiler running the demo traffic program
        # if we can't find the 'Austin' interface, just end test
        ip_address = None
        devices = self.profiler.api.devices.get_all()
        for d in devices:
            if 'sh-austin' in d['name'].lower():
                ip_address = d['ipaddr']
        if not ip_address:
            return

        columns = ['device',
                   'avg_bytes',
                   'total_bytes']
        self.groupby = 'dev'

        with WANSummaryReport(self.profiler) as report:
            lan_address, wan_address = report.get_interfaces(ip_address)
            self.assertTrue(lan_address)
            self.assertTrue(wan_address)

            report.run(lan_address, wan_address, 'inbound', columns=columns,
                       groupby=self.groupby,
                       timefilter=self.yesterday)
            inbound = report.get_data(as_list=False)

            self.assertEqual(inbound.shape, (1,4))
            self.assertTrue(all(inbound.LAN_avg_bytes > inbound.WAN_avg_bytes))

            report.run(lan_address, wan_address, 'outbound', columns=columns,
                       groupby=self.groupby,
                       timefilter=self.yesterday)
            outbound = report.get_data(as_list=False)
            self.assertEqual(outbound.shape, (1,4))
            self.assertTrue(all(outbound.LAN_avg_bytes > outbound.WAN_avg_bytes))


class ProfilerDevicesTests(unittest.TestCase):
    def setUp(self):
        self.profiler = create_profiler()
        # common header fields for device lists
        self.headernames = ['name', 'type_id', 'ipaddr', 'version', 'type', 'id']

    def test_typelist(self):
        """Check that get_types returns list of two-tuples"""
        types = self.profiler.api.devices.get_types()
        self.assertEqual(len(types[0]), 2)

    def test_getdevices(self):
        """Verify list of dicts for devices returned on get_all query"""
        devices = self.profiler.api.devices.get_all()
        dev0 = devices[0]
        self.assertTrue(isinstance(dev0, dict))
        for h in self.headernames:
            self.assertTrue(h in dev0.keys())

    def test_getdevices_by_type(self):
        """Verify list of dicts for devices returned on get_all filtered query"""
        # pull type id from first item in list, then confirm its included
        # when filtering on its type id
        devices = self.profiler.api.devices.get_all()
        dev0 = devices[0]
        typeid = dev0['type_id']
        filtered = self.profiler.api.devices.get_all(typeid=typeid)
        self.assertTrue(dev0 in filtered)

    def test_getdevices_by_cidr(self):
        """Verify list of dicts for devices returned on get_all filtered query"""
        # pull ip from first result, and check its in the result set when
        # querying for that
        devices = self.profiler.api.devices.get_all()
        dev0 = devices[0]
        ipaddr = dev0['ipaddr']
        root = ipaddr.split('.')[0]
        query = '%s.0.0.0/8' % root
        filtered = self.profiler.api.devices.get_all(cidr=query)
        self.assertTrue(dev0 in filtered)
        empty = self.profiler.api.devices.get_all(cidr='10.0.0.0/32')
        self.assertFalse(empty)

    def test_getdetails(self):
        """Verify query by ip address returns single result"""
        devices = self.profiler.api.devices.get_all()
        ipaddr = devices[0]['ipaddr']
        dev = self.profiler.api.devices.get_details(ipaddr)
        self.assertTrue(isinstance(dev, dict))
        for h in self.headernames:
            self.assertTrue(h in dev.keys())


if __name__ == '__main__':
    # for standalone use take one command-line argument: the profiler host
    import sys
    assert len(sys.argv) == 2

    config = {'profilerhost': sys.argv[1]}
    sys.argv = [sys.argv[0]]

    unittest.main()

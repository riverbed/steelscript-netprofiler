# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import pandas
import logging

from steelscript.appfwk.apps.datasource.modules.analysis import \
    AnalysisTable, AnalysisQuery

logger = logging.getLogger(__name__)


def process_interface_dns_elem(interface_dns):
    parts = interface_dns.split("|")
    ip = parts[0]
    name = parts[1]
    ifindex = parts[2]
    if name is not "":
        return name + ":" + ifindex
    else:
        return ip + ":" + ifindex


def process_interface_dns(target, tables, criteria, params):
    table = tables['table']
    table['interface_dns'] = table['interface_dns'].map(process_interface_dns_elem)
    return table


def explode_interface_dns(interface_dns):
    parts = interface_dns.split("|")
    ip = parts[0]
    ifindex = parts[2]
    ifdescr = parts[4]
    return ip, ifindex, ifdescr


class ProfilerMergeIpDeviceTable(AnalysisTable):

    class Meta:
        proxy = True
        app_label = 'steelscript.netprofiler.appfwk'

    _query_class = 'ProfilerMergeIpDeviceQuery'

    @classmethod
    def create(cls, name, devices, traffic, **kwargs):
        kwargs['tables'] = {'devices': devices,
                            'traffic' : traffic}
        return super(ProfilerMergeIpDeviceTable, cls).create(name, **kwargs)

    def post_process_table(self, field_options):
        super(ProfilerMergeIpDeviceTable, self).post_process_table(field_options)
        self.add_column('interface_name', 'Interface', iskey=True,
                        datatype="string")
        self.copy_columns(self.options['tables']['traffic'],
                          except_columns=['interface_dns'])


class ProfilerMergeIpDeviceQuery(AnalysisQuery):

    def post_run(self):
        dev = self.tables['devices']
        tr = self.tables['traffic']

        if tr is None or len(tr) == 0:
            self.data = None
            return True

        if dev is None or len(dev) == 0:
            self.data = tr
            return True

        dev = dev.copy()
        tr['interface_ip'], tr['interface_index'], tr['interface_ifdescr'] = \
            zip(*tr['interface_dns'].map(explode_interface_dns))

        df = pandas.merge(tr, dev,
                          left_on='interface_ip',
                          right_on='ipaddr',
                          how='left')

        # Set the name to the ip addr wherever the name is empty
        nullset = ((df['name'].isnull()) | (df['name'] == ''))
        df.ix[nullset, 'name'] = df.ix[nullset, 'interface_ip']

        # Set ifdescr to the index if empty
        df['ifdescr'] = df['interface_ifdescr']
        nullset = ((df['ifdescr'].isnull()) | (df['ifdescr'] == ''))
        df.ix[nullset, 'ifdescr'] = df.ix[nullset, 'interface_index']

        # Compute the name from the name and ifdescr
        df['interface_name'] = (df['name'].astype(str) +
                                ':' +
                                df['ifdescr'].astype(str))

        self.data = df
        return True

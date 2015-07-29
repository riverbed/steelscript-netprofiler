# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""
The Host Group module provides an interface for manipulating host group types
and their host groups and hosts.
"""

import re

from steelscript.netprofiler.core import _constants
from steelscript.netprofiler.core.report import SingleQueryReport

service_tree_key_ctxt_re = re.compile(
    '^(?P<col_id>[0-9]+):(?P<elem_id>[0-9:]+)\|(?P<elem_name>[^[]+)')

COL_ID_LOCATION = 691
COL_ID_METRIC_CAT = 692

service_health_ctxt_location_re = re.compile(
    '(?P<health>[0-9]*)\*?'
    '\[service_location_id=(?P<location_id>[0-9:]+)'
    '\[svc_location_id')


service_health_ctxt_location_service_re = re.compile(
    '(?P<health>[0-9]*)\*?'
    '\[service_location_id=(?P<location_id>[0-9:]+)'
    ',service_id=(?P<service_id>[0-9]+)'
    '\[svc_location_id')

service_health_ctxt_metric_cat_re = re.compile(
    '([0-9]*)\*?\[service_location_id=([0-9:]+)'
    ',metric_cat_id=([0-9])+'
    '\[svc_metric_cat_id')

service_health_ctxt_metric_cat_service_re = re.compile(
    '([0-9]*)\*?\[service_location_id=([0-9:]+)'
    ',metric_cat_id=([0-9])+'
    ',service_id=([0-9]+)'
    '\[svc_metric_cat_id')


class Service(object):
    SVC_NOT_AVAILABLE = 0
    SVC_DISABLED = 1
    SVC_INIT = 2
    SVC_NORMAL = 3
    SVC_LOW = 4
    SVC_MED = 5       # supposedly ignored
    SVC_HIGH = 6
    SVC_NODATA = 7


class ServiceLocationReport(SingleQueryReport):

    COLUMNS = ['idx', 'parent_id',
               'tree_key_ctxt', 'tree_key_id', 'tree_key_type',
               'health_ctxt']

    def run(self, **kwargs):
        # Key kwargs: timefilter, sync
        super(ServiceLocationReport, self).run(
            groupby='slm',
            realm='msq',
            columns=self.COLUMNS,
            **kwargs)

    def _get_parsed_data(self):
        raw = super(ServiceLocationReport, self).get_data()

        # Raw data comes back with the following columns:
        #   idx                - row index
        #   parent_id          - parent index (blank for location summary)
        #   tree_key_ctxt      - the context for this row, either a location
        #                        or a metric category
        #   tree_key_id        - the location id or metric cat id for this row
        #   tree_key_type      - the type of row, location or metric cat
        #   health_ctxt        - the actual health, plus full context
        #   [svc_health_ctxt]  - health_ctxt for each service

        pos = {'svc_health_ctxt': []}
        for i, l in enumerate(self.get_legend()):
            if l.id < _constants.EPHEMERAL_COLID:
                pos[l.key] = i
            else:
                pos['svc_health_ctxt'].append([i, l.json['name']])

        rows = []
        for rawrow in raw:
            row = {}
            row['id'] = rawrow[pos['idx']]
            try:
                row['parent_id'] = int(rawrow[pos['parent_id']])
            except ValueError:
                row['parent_id'] = None

            m = service_tree_key_ctxt_re.match(rawrow[pos['tree_key_ctxt']])
            if not m:
                raise ValueError('Failed to parse tree_key_ctxt for row: %s' %
                                 (rawrow[pos['tree_key_ctxt']]))

            if int(m.group('col_id')) != COL_ID_LOCATION:
                # For now, skip sub-levels that are metric categories
                continue

            (byloc, location) = m.group('elem_name').split(':')
            row['location'] = location

            m = service_health_ctxt_location_re.match(
                rawrow[pos['health_ctxt']])
            if not m:
                raise ValueError('Failed to parse overall health_ctxt: %s' %
                                 (rawrow[pos['health_ctxt']]))

            try:
                h = int(m.group('health'))
            except ValueError:
                h = Service.SVC_NOT_AVAILABLE

            row['overall'] = h

            row['services'] = {}
            for idx, svc_name in pos['svc_health_ctxt']:
                m = service_health_ctxt_location_service_re.match(rawrow[idx])
                if not m:
                    raise ValueError(
                        'Failed to parse service %s (%s) health_ctx: %s' %
                        (svc_name, i, rawrow[idx]))

                try:
                    h = int(m.group('health'))
                except ValueError:
                    h = Service.SVC_NOT_AVAILABLE
                row['services'][svc_name] = h

            rows.append(row)

        return rows

    def get_data(self):
        parsed_rows = self._get_parsed_data()

        rows = []
        for prow in parsed_rows:
            row = {}
            row['location'] = prow['location']
            for svc, health in prow['services'].iteritems():
                row[svc] = health
            rows.append(row)

        return rows

# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import time
import logging
import threading
import datetime

import steelscript.netprofiler.core
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.common.timeutils import (parse_timedelta,
                                          timedelta_total_seconds)
from steelscript.appfwk.apps.datasource.models import \
    DatasourceTable, Column, TableQueryBase
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.apps.devices.forms import fields_add_device_selection
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.datasource.forms import (fields_add_time_selection,
                                                          fields_add_resolution)
from steelscript.appfwk.libs.fields import Function


logger = logging.getLogger(__name__)
lock = threading.Lock()


def _post_process_combine_filterexprs(form, id, criteria, params):
    exprs = []
    if ('netprofiler_filterexpr' in criteria and
            criteria.netprofiler_filterexpr != ''):
        exprs.append(criteria.netprofiler_filterexpr)

    field = form.get_tablefield(id)
    for parent in field.parent_keywords:
        expr = criteria[parent]
        if expr is not None and expr != '':
            exprs.append(expr)

    if len(exprs) == 0:
        val = ""
    elif len(exprs) == 1:
        val = exprs[0]
    else:
        val = "(" + ") and (".join(exprs) + ")"

    criteria['netprofiler_filterexpr'] = val


class NetProfilerTable(DatasourceTable):

    class Meta:
        proxy = True
    _query_class = 'NetProfilerQuery'

    TABLE_OPTIONS = {'groupby': None,
                     'realm': None,
                     'interface': None}

    # default field parameters
    FIELD_OPTIONS = {'duration': 60,
                     'durations': None,
                     'resolution': 'auto',
                     'resolutions': (('auto', 'Automatic'),
                                     '1min', '15min', 'hour', '6hour'),
                     }

    def post_process_table(self, field_options):
        resolution = field_options['resolution']
        if resolution != 'auto':
            if isinstance(resolution, int):
                res = resolution
            else:
                res = int(timedelta_total_seconds(parse_timedelta(resolution)))
            resolution = steelscript.netprofiler.core.report.Report.RESOLUTION_MAP[res]
            field_options['resolution'] = resolution

        fields_add_device_selection(self, keyword='netprofiler_device',
                                    label='NetProfiler', module='netprofiler',
                                    enabled=True)

        duration = field_options['duration']
        if isinstance(duration, int):
            duration = "%d min" % duration

        fields_add_time_selection(self,
                                  initial_duration=duration,
                                  durations=field_options['durations'])

        fields_add_resolution(self,
                              initial=field_options['resolution'],
                              resolutions=field_options['resolutions'],
                              special_values=['auto'])
        self.fields_add_filterexpr()

    def fields_add_filterexpr(self, keyword='netprofiler_filterexpr',
                              initial=None):
        field = TableField(keyword=keyword,
                           label='NetProfiler Filter Expression',
                           help_text=('Traffic expression using NetProfiler '
                                      'Advanced Traffic Expression syntax'),
                           initial=initial,
                           required=False)
        field.save()
        self.fields.add(field)

    def fields_add_filterexprs_field(self, keyword):

        field = self.fields.get(keyword='netprofiler_filterexpr')
        field.post_process_func = Function(
            function=_post_process_combine_filterexprs
        )

        parent_keywords = set(field.parent_keywords or [])
        parent_keywords.add(keyword)
        field.parent_keywords = list(parent_keywords)
        field.save()

        return field

    @staticmethod
    def _post_process_combine_filterexprs(form, id, criteria, params):
        exprs = []
        if ('netprofiler_filterexpr' in criteria and
                criteria.netprofiler_filterexpr != ''):
            exprs.append(criteria.netprofiler_filterexpr)

        field = form.get_tablefield(id)
        for parent in field.parent_keywords:
            expr = criteria[parent]
            if expr is not None and expr != '':
                exprs.append(expr)

        if len(exprs) == 0:
            val = ""
        elif len(exprs) == 1:
            val = exprs[0]
        else:
            val = "(" + ") and (".join(exprs) + ")"

        criteria['netprofiler_filterexpr'] = val


class NetProfilerTimeSeriesTable(NetProfilerTable):
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'groupby': 'time',
                     'realm': 'traffic_overall_time_series',
                     'interface': None}


class NetProfilerGroupbyTable(NetProfilerTable):
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'groupby': None,
                     'realm': 'traffic_summary',
                     'interface': None}


class NetProfilerQuery(TableQueryBase):

    def fake_run(self):
        import fake_data
        self.data = fake_data.make_data(self.table, self.job)

    def run(self):
        """ Main execution method
        """
        criteria = self.job.criteria

        if criteria.netprofiler_device == '':
            logger.debug('%s: No netprofiler device selected' % self.table)
            self.job.mark_error("No NetProfiler Device Selected")
            return False

        #self.fake_run()
        #return True

        profiler = DeviceManager.get_device(criteria.netprofiler_device)
        report = steelscript.netprofiler.core.report.SingleQueryReport(profiler)

        columns = [col.name for col in self.table.get_columns(synthetic=False)]

        sortcol = None
        if self.table.sortcols is not None:
            sortcol = self.table.sortcols[0]

        tf = TimeFilter(start=criteria.starttime,
                        end=criteria.endtime)

        logger.info("Running NetProfiler table %d report for timeframe %s" %
                    (self.table.id, str(tf)))

        if ('datafilter' in criteria) and (criteria.datafilter is not None):
            datafilter = criteria.datafilter.split(',')
        else:
            datafilter = None

        trafficexpr = TrafficFilter(
            self.job.combine_filterexprs(exprs=criteria.netprofiler_filterexpr)
        )

        # Incoming criteria.resolution is a timedelta
        logger.debug('NetProfiler report got criteria resolution %s (%s)' %
                     (criteria.resolution, type(criteria.resolution)))
        if criteria.resolution != 'auto':
            rsecs = int(timedelta_total_seconds(criteria.resolution))
            resolution = steelscript.netprofiler.core.report.Report.RESOLUTION_MAP[rsecs]
        else:
            resolution = 'auto'

        logger.debug('NetProfiler report using resolution %s (%s)' %
                     (resolution, type(resolution)))

        with lock:
            centricity = 'int' if self.table.options.interface else 'hos'
            report.run(realm=self.table.options.realm,
                       groupby=profiler.groupbys[self.table.options.groupby],
                       centricity=centricity,
                       columns=columns,
                       timefilter=tf,
                       trafficexpr=trafficexpr,
                       data_filter=datafilter,
                       resolution=resolution,
                       sort_col=sortcol,
                       sync=False
                       )

        done = False
        logger.info("Waiting for report to complete")
        while not done:
            time.sleep(0.5)
            with lock:
                s = report.status()

            self.job.safe_update(progress=int(s['percent']))
            done = (s['status'] == 'completed')

        # Retrieve the data
        with lock:
            query = report.get_query_by_index(0)
            self.data = query.get_data()

            tz = criteria.starttime.tzinfo
            # Update criteria
            criteria.starttime = (datetime.datetime
                                  .utcfromtimestamp(query.actual_t0)
                                  .replace(tzinfo=tz))
            criteria.endtime = (datetime.datetime
                                .utcfromtimestamp(query.actual_t1)
                                .replace(tzinfo=tz))

        self.job.safe_update(actual_criteria=criteria)

        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True

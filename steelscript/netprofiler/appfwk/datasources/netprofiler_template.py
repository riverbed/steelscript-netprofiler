# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import time
import logging
import threading
import datetime

import pandas

from steelscript.appfwk.apps.jobs import QueryComplete
from steelscript.appfwk.apps.report.models import Report
from steelscript.common.timeutils import timedelta_total_seconds
from steelscript.appfwk.apps.datasource.models import TableQueryBase
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.netprofiler.appfwk.datasources.netprofiler import NetProfilerTable
from steelscript.netprofiler.core.report import MultiQueryReport

logger = logging.getLogger(__name__)
lock = threading.Lock()


class NetProfilerTemplateTable(NetProfilerTable):
    class Meta:
        proxy = True

    _query_class = 'NetProfilerTemplateQuery'

    TABLE_OPTIONS = {'template_id': None}


class NetProfilerTemplateQuery(TableQueryBase):
    # Used by Table to actually run a query

    def _prepare_report_args(self):
        class Args(object):
            pass
        args = Args()

        criteria = self.job.criteria

        if criteria.netprofiler_device == '':
            logger.debug('%s: No netprofiler device selected' % self.table)
            self.job.mark_error("No NetProfiler Device Selected")
            return False

        args.profiler = DeviceManager.get_device(criteria.netprofiler_device)

        args.columns = [col.name for col
                        in self.table.get_columns(synthetic=False)]

        args.sortcol = None
        if self.table.sortcols is not None:
            args.sortcol = self.table.sortcols[0]

        args.timefilter = TimeFilter(start=criteria.starttime,
                                     end=criteria.endtime)

        logger.info("Running NetProfiler table %d report for timeframe %s" %
                    (self.table.id, str(args.timefilter)))

        args.trafficexpr = TrafficFilter(
            self.job.combine_filterexprs(exprs=criteria.netprofiler_filterexpr)
        )

        # Incoming criteria.resolution is a timedelta
        logger.debug('NetProfiler report got criteria resolution %s (%s)' %
                     (criteria.resolution, type(criteria.resolution)))
        if criteria.resolution != 'auto':
            rsecs = int(timedelta_total_seconds(criteria.resolution))
            args.resolution = Report.RESOLUTION_MAP[rsecs]
        else:
            args.resolution = 'auto'

        logger.debug('NetProfiler report using resolution %s (%s)' %
                     (args.resolution, type(args.resolution)))

        return args

    def _wait_for_data(self, report, minpct=0, maxpct=100):
        criteria = self.job.criteria
        done = False
        logger.info("Waiting for report to complete")
        while not done:
            time.sleep(0.5)
            with lock:
                s = report.status()

            logger.debug('Status: XXX %s' % str(s))
            pct = int(float(s['percent']) * ((maxpct - minpct)/100.0) + minpct)
            self.job.mark_progress(progress=pct)
            done = (s['status'] == 'completed')

        # Retrieve the data
        with lock:
            query = report.get_query_by_index(0)
            data = query.get_data()

            tz = criteria.starttime.tzinfo
            # Update criteria
            criteria.starttime = (datetime.datetime
                                  .utcfromtimestamp(query.actual_t0)
                                  .replace(tzinfo=tz))
            criteria.endtime = (datetime.datetime
                                .utcfromtimestamp(query.actual_t1)
                                .replace(tzinfo=tz))

        self.job.safe_update(actual_criteria=criteria)
        return data

    def run(self):
        """ Main execution method. """
        args = self._prepare_report_args()

        with lock:
            report = MultiQueryReport(args.profiler)
            report.run(template_id=self.table.options.template_id,
                       timefilter=args.timefilter,
                       trafficexpr=args.trafficexpr,
                       resolution=args.resolution)

        data = self._wait_for_data(report)
        headers = report.get_legend()

        # create dataframe with all of the default headers
        df = pandas.DataFrame(data, columns=[h.key for h in headers])

        # now filter down to the columns requested by the table
        columns = [col.name for col in self.table.get_columns(synthetic=False)]
        df = df[columns]

        logger.info("Report %s returned %s rows" % (self.job, len(df)))
        return QueryComplete(df)

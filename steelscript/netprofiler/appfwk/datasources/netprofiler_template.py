# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
import threading
import datetime

import pandas

import steelscript
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.common.timeutils import timedelta_total_seconds
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.netprofiler.appfwk.datasources.netprofiler import NetProfilerTable


logger = logging.getLogger(__name__)
lock = threading.Lock()


class NetProfilerTemplateTable(NetProfilerTable):
    class Meta:
        proxy = True

    _query_class = 'NetProfilerTemplateQuery'

    TABLE_OPTIONS = {'template_id': None}


class NetProfilerTemplateQuery(TableQueryBase):
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        """ Main execution method. """
        criteria = self.job.criteria

        if criteria.netprofiler_device == '':
            logger.debug('%s: No netprofiler device selected' % self.table)
            self.job.mark_error("No NetProfiler Device Selected")
            return False

        profiler = DeviceManager.get_device(criteria.netprofiler_device)
        report = steelscript.netprofiler.core.report.MultiQueryReport(profiler)

        tf = TimeFilter(start=criteria.starttime,
                        end=criteria.endtime)

        logger.info("Running NetProfilerTemplateTable table %d report "
                    "for timeframe %s" % (self.table.id, str(tf)))

        trafficexpr = TrafficFilter(
            self.job.combine_filterexprs(exprs=criteria.profiler_filterexpr)
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
            res = report.run(template_id=self.table.options.template_id,
                             timefilter=tf,
                             trafficexpr=trafficexpr,
                             resolution=resolution)

        if res is True:
            logger.info("Report template complete.")
            self.job.safe_update(progress=100)

        # Retrieve the data
        with lock:
            query = report.get_query_by_index(0)
            data = query.get_data()
            headers = report.get_legend()

            tz = criteria.starttime.tzinfo
            # Update criteria
            criteria.starttime = (datetime.datetime
                                  .utcfromtimestamp(query.actual_t0)
                                  .replace(tzinfo=tz))
            criteria.endtime = (datetime.datetime
                                .utcfromtimestamp(query.actual_t1)
                                .replace(tzinfo=tz))

        self.job.safe_update(actual_criteria=criteria)

        # create dataframe with all of the default headers
        df = pandas.DataFrame(data, columns=[h.key for h in headers])

        # now filter down to the columns requested by the table
        columns = [col.name for col in self.table.get_columns(synthetic=False)]
        self.data = df[columns]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True

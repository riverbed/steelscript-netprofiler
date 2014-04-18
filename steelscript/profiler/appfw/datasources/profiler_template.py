# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import time
import logging
import threading
import datetime
import pandas

import steelscript
from steelscript.profiler.core.filters import TimeFilter, TrafficFilter
from steelscript.common.timeutils import timedelta_total_seconds

from rvbd_portal.apps.devices.devicemanager import DeviceManager
from steelscript.profiler.appfw.datasources.profiler import ProfilerTable

logger = logging.getLogger(__name__)
lock = threading.Lock()


class ProfilerTemplateTable(ProfilerTable):
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'template_id': None}


class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        """ Main execution method. """
        criteria = self.job.criteria

        if criteria.profiler_device == '':
            logger.debug('%s: No profiler device selected' % self.table)
            self.job.mark_error("No Profiler Device Selected")
            return False
            
        profiler = DeviceManager.get_device(criteria.profiler_device)
        report = steelscript.profiler.core.report.MultiQueryReport(profiler)

        tf = TimeFilter(start=criteria.starttime,
                        end=criteria.endtime)

        logger.info("Running ProfilerTemplateTable table %d report "
                    "for timeframe %s" % (self.table.id, str(tf)))

        trafficexpr = TrafficFilter(
            self.job.combine_filterexprs(exprs=criteria.profiler_filterexpr)
        )

        # Incoming criteria.resolution is a timedelta
        logger.debug('Profiler report got criteria resolution %s (%s)' %
                     (criteria.resolution, type(criteria.resolution)))
        if criteria.resolution != 'auto':
            rsecs = int(timedelta_total_seconds(criteria.resolution))
            resolution = steelscript.profiler.core.report.Report.RESOLUTION_MAP[rsecs]
        else:
            resolution = 'auto'
        
        logger.debug('Profiler report using resolution %s (%s)' %
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

        if self.table.sortcol is not None:
            self.data = self.data.sort(self.table.sortcol.name)

        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True

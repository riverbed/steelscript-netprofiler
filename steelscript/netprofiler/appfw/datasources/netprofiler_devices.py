# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging
import pandas
import datetime

from steelscript.appfw.core.apps.datasource.models import DatasourceTable
from steelscript.appfw.core.apps.devices.devicemanager import DeviceManager
from steelscript.appfw.core.apps.devices.forms import fields_add_device_selection
from steelscript.appfw.core.libs.fields import Function

import steelscript
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.netprofiler.appfw.datasources.netprofiler import lock

logger = logging.getLogger(__name__)


class NetProfilerDeviceTable(DatasourceTable):
    class Meta:
        proxy = True

    def post_process_table(self, field_options):
        self.criteria_handle_func = Function(criteria_handle)
        self.save()
        fields_add_device_selection(self, keyword='netprofiler_device',
                                    label='NetProfiler', module='netprofiler',
                                    enabled=True)


def criteria_handle(criteria, **kwargs):
    kvs = {}
    kvs['netprofiler_device'] = criteria.netprofiler_device
    today = datetime.datetime.now().replace(hour=0, minute=0,
                                            second=0, microsecond=0)
    kvs['date'] = today
    return kvs


class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def fake_run(self):
        import fake_data
        self.data = fake_data.make_data(self.table)

    def run(self):
        """ Main execution method
        """

        criteria = self.job.criteria

        if criteria.netprofiler_device == '':
            logger.debug('%s: No netprofiler device selected' % (self.table))
            self.job.mark_error("No NetProfiler Device Selected")
            return False

        profiler = DeviceManager.get_device(criteria.netprofiler_device)

        columns = [col.name for col in self.table.get_columns(synthetic=False)]

        # This returns an array of rows, one row per device
        # Each row is a dict containing elements such as:
        #      id, ipaddr, name, type, type_id, and version
        with lock:
            devicedata = profiler.api.devices.get_all()

        # Convert to a DataFrame to make it easier to work with
        df = pandas.DataFrame(devicedata)

        for col in columns:
            if col not in df:
                raise KeyError("Devices table has no column '%s'" % col.name)

        df = df.ix[:,columns]

        if self.table.sortcol is not None:
            df = df.sort(self.table.sortcol.name)

        if self.table.rows > 0:
            df = df[:self.table.rows]

        self.data = df

        logger.info("DeviceTable job %s returning %d devices" % (self.job, len(self.data)))
        return True

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging
import pandas as pd

from steelscript.appfwk.apps.datasource.models import DatasourceTable,\
    TableQueryBase, TableField, Column
from steelscript.appfwk.apps.devices.forms import fields_add_device_selection
from steelscript.appfwk.apps.jobs import QueryComplete
from steelscript.appfwk.apps.datasource.forms import \
    fields_add_time_selection
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.devices.models import Device
from steelscript.appfwk.apps.datasource.forms import IDChoiceField
from steelscript.netprofiler.core._constants import EPHEMERAL_COLID
from steelscript.netprofiler.core.report import LiveReport
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
import steelscript.appfwk.apps.report.modules.yui3 as yui3

logger = logging.getLogger(__name__)


def netprofiler_live_templates(form, id, field_kwargs):
    """Query netprofiler for available live templates. """
    netprofiler_device = form.get_field_value('netprofiler_device', id)
    if netprofiler_device == '':
        choices = [('', '<No netprofiler device>')]
    else:
        netprofiler = DeviceManager.get_device(netprofiler_device)

        choices = [(t['id'], t['name'])
                   for t in netprofiler.api.templates.get_live_templates()]

    field_kwargs['choices'] = choices
    field_kwargs['label'] = 'Live Template'


class NetProfilerLiveConfigTable(DatasourceTable):
    class Meta:
        proxy = True

    _query_class = 'NetProfilerLiveConfigQuery'

    def post_process_table(self, field_options):
        fields_add_device_selection(self, keyword='netprofiler_device',
                                    label='NetProfiler', module='netprofiler',
                                    enabled=True)
        fields_add_time_selection(self, show_end=True, show_duration=False)

        func = Function(netprofiler_live_templates, self.options)

        TableField.create('template_id', label='Template',
                          obj=self,
                          field_cls=IDChoiceField,
                          parent_keywords=['netprofiler_device'],
                          dynamic=True,
                          pre_process_func=func)

        self.add_column('template_id', 'Template ID', datatype='string',
                        iskey=True)
        self.add_column('widget_id', 'Widget ID', datatype='integer',
                        iskey=True)
        self.add_column('title', 'Title', datatype='string')
        self.add_column('widget_type', 'Type', datatype='string')
        self.add_column('visualization', 'Visualization', datatype='string')
        self.add_column('datasource', 'Data Source', datatype='string')


class NetProfilerLiveConfigQuery(TableQueryBase):

    def run(self):

        criteria = self.job.criteria
        profiler = DeviceManager.get_device(criteria.netprofiler_device)
        widget_config = profiler.api.templates.get_config(criteria.template_id)
        recs = []
        for w in widget_config:
            dict0 = {'template_id': str(criteria.template_id)}
            dict1 = dict((k, w[k]) for k in ['widget_id', 'title'])
            dict2 = dict((k, w['config'][k]) for k in
                         ['widget_type', 'visualization', 'datasource'])
            recs.append(dict((k, v) for d in [dict0, dict1, dict2]
                             for k, v in d.iteritems()))

        return QueryComplete(pd.DataFrame(recs))


class NetProfilerLiveTable(DatasourceTable):
    class Meta:
        proxy = True

    _query_class = 'NetProfilerLiveQuery'

    TABLE_OPTIONS = {'netprofiler_id': None,
                     'template_id': None,
                     'query_id': None,
                     'widget_id': None
                     }


class NetProfilerLiveQuery(TableQueryBase):

    def run(self):

        # For each of the widget, get all the data
        profiler = DeviceManager.get_device(self.table.options.netprofiler_id)

        lr = LiveReport(profiler, template_id=self.table.options.template_id)

        # Figure out columns by querying the widget
        # cols = lr.get_columns(self.table.options.widget_id)

        # Find the query object
        query_idx = lr.get_query_names().index(self.table.options.query_id)

        # refresh the columns of the table
        self._refresh_columns(profiler, report=lr, query=lr.queries[query_idx])

        data = lr.get_data(index=query_idx)

        col_names = [col.label if col.ephemeral else col.key
                     for col in lr.queries[query_idx].columns]

        df = pd.DataFrame(columns=col_names, data=data)

        return QueryComplete(df)

    def _refresh_columns(self, profiler, report, query):

        # Delete columns
        for col in self.table.get_columns():
            col.delete()

        cols = []
        for col in query.columns:
            if col.id >= EPHEMERAL_COLID:
                cols.append(col)

        if not cols:
            cols = report.get_columns(self.table.options.widget_id)

        if query.is_time_series:
            # 98 is the column id for 'time'
            cols = [profiler.columns[98]] + cols

        for col in cols:
            if (col.json['type'] == 'float' or
                    col.json['type'] == 'reltime' or
                    col.json['rate'] == 'opt'):

                data_type = 'float'

            elif col.json['type'] == 'time':
                data_type = 'time'

            elif col.json['type'] == 'int':
                data_type = 'integer'

            else:
                data_type = 'string'

            col_name = col.label if col.ephemeral else col.key
            Column.create(self.table, col_name, col.label,
                          datatype=data_type, iskey=col.iskey)


def add_widgets_to_live_report(report, template_id, widget_query_ids,
                               netprofiler_name=None):

    if netprofiler_name:
        netprofiler_id = Device.objects.filter(name=netprofiler_name)[0].id
    else:
        netprofiler_id = Device.objects.\
            filter(enabled=True, module='netprofiler')[0].id

    profiler = DeviceManager.get_device(netprofiler_id)

    lr = LiveReport(profiler, template_id)

    for wid, qid in widget_query_ids.iteritems():
        q = [q for q in lr.queries if q.id.endswith(qid)][0]
        t = NetProfilerLiveTable.create(
            'live-{0}-{1}'.format(template_id, wid),
            netprofiler_id=netprofiler_id,
            template_id=template_id,
            query_id=q.id,
            widget_id=wid,
            cacheable=False)

        if q.is_time_series:
            widget_cls = yui3.TimeSeriesWidget
            t.add_column('time', 'Time', datatype='time', iskey=True)
        else:
            widget_cls = yui3.TableWidget

        widget_title = 'Template %s Widget %s' % (template_id, wid)
        report.add_widget(widget_cls, t, widget_title, width=12)

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


"""
This module defines Profiler Report and Query objects which provide
access to running reports and retrieving data from a Profiler.
"""

import logging
import re
import time

from rvbd.profiler.filters import TimeFilter
from rvbd.common.timeutils import *
from rvbd.common.utils import RecursiveUpdateDict

__all__ = ['TrafficSummaryReport',
           'TrafficOverallTimeSeriesReport',
           'TrafficFlowListReport',
           'IdentityReport']

logger = logging.getLogger(__name__)


class Query(object):
    """This class represents a profiler query instance.
    """
    def __init__(self, report, query, column_ids=None):
        self.report = report
        self.id = query['id']
        self.actual_t0 = query['actual_t0']
        self.actual_t1 = query['actual_t1']

        # find the columns in query which indicate they are 'available'
        # or have been computed as part of the request
        # TODO this part of the API should be reviewed with profiler team
        query_columns = [q for q in query['columns'] if q['available']]

        self.available_columns = self.report.profiler.get_columns(query_columns)

        if column_ids:
            self.selected_columns = self.report.profiler.get_columns_by_ids(column_ids)
        else:
            self.selected_columns = None

        self.querydata = None
        self.data = None
        self.data_selected_columns = None

    def get_legend(self, columns=None):
        if columns:
            return self.report.profiler.get_columns(columns)
        if self.selected_columns:
            return self.selected_columns
        return self.available_columns

    def _to_native(self, row):
        legend = self.get_legend()
        for i, x in enumerate(row):
            if legend[i].json['type'] == 'int':
                row[i] = int(x)
            elif (legend[i].json['type'] == 'float' or
                  legend[i].json['type'] in 'reltime'):
                try:
                    row[i] = float(x)
                except ValueError:
                    pass
        return row

    def _get_querydata(self, columns=None):
        """Get the query data.
        """
        if columns:
            columns = self.report.profiler.get_columns(columns)
        elif self.selected_columns is not None:
            columns = self.selected_columns

        #if we already got this data do not get it again
        changed = (self.data_selected_columns is None or
                   self.data_selected_columns != columns)
        if not changed:
            return
        if columns:
            params = {"columns": (",".join(str(col.id)
                                           for col in columns))}
        else:
            params = None

        self.querydata = self.report.profiler.api.report.queries(self.report.id,
                                                                 self.id,
                                                                 params=params)
        self.data = self.querydata['data']
        self.data_selected_columns = columns
        logger.debug(
            'Retrieved query data for '
            'query id {0} and column {1}'.format(self.id, columns))

    def get_iterdata(self, columns=None):
        """Iterate over the query data
        """
        self._get_querydata(columns)
        for row in self.data:
            yield self._to_native(row)

    def get_data(self, columns=None):
        return list(self.get_iterdata(columns))

    def get_totals(self, columns=None):
        """Return the totals associated with the requested columns.
        """
        self._get_querydata(columns)
        return self._to_native(self.querydata['totals'])
        
    def all_columns(self):
        """Returns all the columns available for this query.
        Used in conjunction with :py:meth:`Query.get_data` or :py:meth:`Query.get_iterdata`
        allows to retrieve all the data available for the query. Eg:

        query.get_iterdata(columns=query.all_columns())
        """
        return self.available_columns


class Report(object):
    """This class represents a Profiler report.  This class is normally not
    used directly, but instead via subclasses for specific report types.
    """

    RESOLUTION_MAP = { 60: "1min",
                       60*15: "15min",
                       60*60: "hour",
                       60*60*6: "6hour",
                       60*60*24: "day",
                       60*60*24*7: "week" }

    # Note that report parameters such as the template id are not set
    # on initialization, but not until run().  This is to accommodate
    # a future load() command which will take a report id and load the
    # parameters of an existing report from Profiler.

    def __init__(self, profiler):
        """Initialize a report object.  A report
        object is bound to an instance of a Profiler at creation.
        """

        self.profiler = profiler

        self.template_id = None
        self.timefilter = None
        self.resolution = None
        self.trafficexpr = None

        self.query = None
        self.queries = list()

    def __enter__(self):
        return self

    def __exit__(self, instype, value, traceback):
        self.delete()

    def run(self, template_id,
            timefilter=None, resolution="auto",
            query=None, trafficexpr=None, data_filter=None, sync=True):
        """Create the report on Profiler and begin running
        the report.  If the `sync` option is True, periodically
        poll until the report is complete, otherwise return
        immediately.

        `template_id` is the numeric id of the template to use for the report

        `timefilter` is the range of time to query, a TimeFilter object
        
        `resolution` is the data resolution (1min, 15min, etc.), defaults to 'auto'

        `query` is the query object containing criteria

        `trafficexpr` is a TrafficFilter object

        `data_filter` is a deprecated filter to run against report data

        `sync` if True, poll for status until the report is complete
        """

        self.template_id = template_id
        if timefilter is None:
            self.timefilter = TimeFilter.parse_range("last 5 min")
        else:
            self.timefilter = timefilter
        self.query = query
        self.trafficexpr = trafficexpr

        self.data_filter = data_filter

        self.id = None
        self.last_status = None


        if resolution not in ["auto", "1min", "15min", "hour",
                              "6hour", "day", "week", "month"]:
            rd = parse_timedelta(resolution)
            resolution = self.RESOLUTION_MAP[int(rd.total_seconds())]

            raise ValueError('resolution "%s" invalid must be one of these values: '
                             'auto, 1min, 15min, hour '
                             '6hour, day, week, month' % resolution)
        self.resolution = resolution

        start = datetime_to_seconds(self.timefilter.start)
        end = datetime_to_seconds(self.timefilter.end)

        #using a RecursiveUpdateDict
        criteria = RecursiveUpdateDict(**{"time_frame": {"start": int(start),
                                                         "end": int(end)}
                                          })

        if self.query is not None:
            criteria["query"] = self.query

        if self.resolution != "auto":
            criteria["time_frame"]["resolution"] = self.resolution

        if self.data_filter:
            criteria['deprecated'] = {self.data_filter[0]: self.data_filter[1]}

        if self.trafficexpr is not None:
            criteria["traffic_expression"] = self.trafficexpr.filter

        to_post = {"template_id": self.template_id,
                   "criteria": criteria}

        logger.debug("Posting JSON: %s" % to_post)

        self.profiler.api.report.reports(data=to_post)

        location = self.profiler.conn.last_http_response.getheader("Location")
        m = re.match(".*reporting/reports/([0-9]+)$", location)
        if not m:
            raise ValueError(
                "failed to retrieve report id from location header: %s"
                % location)

        self.id = int(m.group(1))
        logger.info("Created report %d" % self.id)

        if sync:
            self.wait_for_complete()

    def wait_for_complete(self, interval=1, timeout=600):
        """ Periodically checks report status and returns when 100% complete
        """
        complete = False
        percent = 100
        start = time.clock()
        while (time.clock() - start) < timeout:
            s = self.status()

            if s['status'] == 'completed':
                logger.info("Report %d complete" % self.id)
                complete = True
                break

            if int(s['percent']) != percent:
                percent = s['percent']
                logger.info("Report %d %d%% complete, remaining %d" %
                            (self.id, percent, s['remaining_seconds']))

            time.sleep(interval)

        if not complete:
            logger.warning("Timed out waiting for report %d to complete,"
                           "last %d%% complete" %
                           (self.id, (percent if percent else 0)))

        return complete

    def status(self):
        """Query for the status of report.  If the report has not been run,
        this returns None.

        The return value is a dict containing:

        `status` indicating `completed` when finished

        `percent` indicating the percentage complete (0-100)

        `remaining_seconds` is an estimate of the time left until complete
        """
        if not self.id:
            return None

        self.last_status = self.profiler.api.report.status(self.id)

        return self.last_status

    def _load_queries(self, column_ids=None):
        if not self.id:
            raise ValueError("No id set, must run a report"
                             "or attach to an existing report first")

        data = self.profiler.api.report.queries(self.id)
        for query in data:
            self.queries.append(Query(self, query, column_ids))

        logger.debug("Report %d: loaded %d queries"
                     % (self.id, len(data)))

    def get_query_by_index(self, index=0):
        """Returns the query_id by specifying the index,
        default to 0 (the first query)
        """
        if not self.id:
            raise ValueError("No id set, must run a report"
                             "or attach to an existing report first")

        if len(self.queries) == 0:
            self._load_queries()

        query = self.queries[index]

        logger.debug("Retrieving query data for report %d, query %s" %
                     (self.id, query.id))

        return query

    def get_legend(self, index=0, columns=None):
        """Return a legend describing the columns that are associated with
        this report.  If `columns` is specified, restrict the legend to
        the list of requested columns.
        """
        query = self.get_query_by_index(index)
        return query.get_legend(columns)

    def get_iterdata(self, index=0, columns=None):
        """Retrieve an iterator on the the data for this report. If
        `columns` is specified, restrict the legend to the list of
        requested columns.
        """
        query = self.get_query_by_index(index)
        return query.get_iterdata(columns)

    def get_data(self, index=0, columns=None):
        """Retrieve the data for this report. If `columns` is specified,
        restrict the data to the list of requested columns.
        """
        query = self.get_query_by_index(index)
        return query.get_data(columns)

    def get_totals(self, index=0, columns=None):
        """Retrieve the totals for this report. If `columns` is specified,
        restrict the totals to the list of requested columns.
        """
        query = self.get_query_by_index(index)
        return query.get_totals(columns)

    def delete(self):
        """Issue a call to Profiler delete this report."""
        if self.id:
            self.profiler.api.report.delete(self.id)


class SingleQueryReport(Report):

    def __init__(self, profiler):
        """Create a report consisting of a single query.  This class is not normally
        instantiated directly.  See child classes such as `TrafficSummaryReport`.

        `profiler` is the Profiler object that will run this report
        """

        super(SingleQueryReport, self).__init__(profiler)

    def run(self, realm,
            groupby="hos", columns=None, sort_col=None,
            timefilter=None, trafficexpr=None, host_group_type="ByLocation",
            resolution="auto", centricity="hos", area=None, data_filter=None, sync=True):
        """
        `realm` is the type of query, this is automatically set by subclasses

        `groupby` sets the way in which data should be grouped (use profiler.groupby.*)

        `columns` is the list of key and value columns to retrieve (use profiler.columns.*)

        `sort_col` is the column within `columns` to sort by

        `timefilter` is the range of time to query, a TimeFilter object

        `trafficexpr` is a TrafficFilter object

        `resolution` is the data resolution (1min, 15min, etc.)

        `host_group_type` sets the host group type to use when the groupby is
            related to groups (such as 'group' or 'peer_group')

        `centricity` is either 'hos' for host-based counts, or 'ifc' for interface
            based counts, this only affects directional columns

        `area` sets the appropriate scope for the report

        `data_filter` is a deprecated filter to run against report data
        """

        # query related parameters
        self.realm = realm
        self.groupby = groupby or 'hos'
        self.columns = columns
        self.sort_col = sort_col
        self.centricity = centricity
        self.host_group_type = host_group_type
        self.area = area

        self._column_ids = [x.id for x in
                            self.profiler.get_columns(self.columns, self.groupby)]

        query = {"realm": self.realm,
                 "centricity": self.centricity,
                 "group_by": self.groupby,
                 "columns": self._column_ids,
                 }

        if self.sort_col is not None:
            query["sort_column"] = [x.id for x in
                                    self.profiler.get_columns([self.sort_col])][0]
        else:
            self._sort_col_id = None

        if self.area is not None:
            query['area'] = self.profiler._parse_area(self.area)

        if self.groupby in ['gro', 'gpp', 'gpr']:
            query['host_group_type'] = self.host_group_type

        super(SingleQueryReport, self).run(template_id=184,
                                           timefilter=timefilter, resolution=resolution,
                                           query=query, trafficexpr=trafficexpr,
                                           data_filter=data_filter,
                                           sync=sync)

    def _load_queries(self):
        super(SingleQueryReport, self)._load_queries(self._column_ids)

    def get_legend(self, columns=None):
        if columns is None:
            columns = self.columns
        return super(SingleQueryReport, self).get_legend(0, columns)

    def get_iterdata(self, columns=None):
        if columns is None:
            columns = self.columns
        return super(SingleQueryReport, self).get_iterdata(0, columns)

    def get_data(self, columns=None):
        if columns is None:
            columns = self.columns
        return super(SingleQueryReport, self).get_data(0, columns)


class TrafficSummaryReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create a traffic summary report.  The data is organized by the requested
        groupby, and retrieves the selected columns. 

        """
        super(TrafficSummaryReport, self).__init__(profiler)

    def run(self, groupby, columns, sort_col=None,
            timefilter=None, trafficexpr=None, host_group_type="ByLocation",
            resolution="auto", centricity="hos", area=None, sync=True):
        """ See `SingleQueryReport` for a description of the arguments. """
        return super(TrafficSummaryReport, self).run(
            realm='traffic_summary',
            groupby=groupby, columns=columns, sort_col=sort_col,
            timefilter=timefilter, trafficexpr=trafficexpr, host_group_type=host_group_type,
            resolution=resolution, centricity=centricity, area=area, sync=sync)


class TrafficOverallTimeSeriesReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create an overall time series report."""
        super(TrafficOverallTimeSeriesReport, self).__init__(profiler)

    def run(self, columns,
            timefilter=None, trafficexpr=None,
            resolution="auto", centricity="hos", area=None, sync=True):
        """
        See `SingleQueryReport` for a description of the arguments.  (Note that
        `sort_col`, `groupby`, and `host_group_type` are not applicable to 
        this report type).
        """
        return super(TrafficOverallTimeSeriesReport, self).run(
            realm='traffic_overall_time_series',
            groupby='tim', columns=columns, sort_col=None,
            timefilter=timefilter, trafficexpr=trafficexpr, host_group_type=None,
            resolution=resolution, centricity=centricity, area=area, sync=sync)


class TrafficFlowListReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create a flow list report."""
        super(TrafficFlowListReport, self).__init__(profiler)

    def run(self, columns, sort_col=None,
            timefilter=None, trafficexpr=None, sync=True):
        """
        See `SingleQueryReport` for a description of the arguments.  (Note that
        only `columns, `sort_col`, `timefilter`, and `trafficexpr` apply to this
        report type).
        """
        return super(TrafficFlowListReport, self).run(
            realm='traffic_flow_list',
            groupby='hos', columns=columns, sort_col=sort_col,
            timefilter=timefilter, trafficexpr=trafficexpr, host_group_type=None,
            resolution="1min", centricity="hos", area=None, sync=sync)


class IdentityReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """ Create a report for Active Directory events.
        """
        super(IdentityReport, self).__init__(profiler)

        self.id_realm = 'identity_list'
        self.id_centricity = 'hos'
        self.id_groupby = 'thu'
        self.id_columns = profiler.get_columns(['time',
                                                'username',
                                                'full_username',
                                                'login_ok',
                                                'host_ip',
                                                'host_dns',
                                                'host_switch',
                                                'host_switch_dns',
                                                'domain'])

    def run(self, username=None, timefilter=None, trafficexpr=None, sync=True):
        """Run complete user identity report over the requested timeframe

        `username` specific id to filter results by

        `timefilter` is the range of time to query, a TimeFilter object

        `trafficexpr` is an optional TrafficFilter object
        """
        if username:
            data_filter = ('user', username)
        else:
            data_filter = None

        super(IdentityReport, self).run(
            realm=self.id_realm,
            groupby=self.id_groupby,
            columns=self.id_columns,
            timefilter=timefilter,
            trafficexpr=trafficexpr,
            centricity=self.id_centricity,
            data_filter=data_filter,
            sync=sync
        )

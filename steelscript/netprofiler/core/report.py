# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


"""
This module defines NetProfiler Report and Query objects which provide
access to running reports and retrieving data from a NetProfiler.
"""

import logging
import time
import types
import cStringIO as StringIO

from steelscript.common.api_helpers import APIVersion
from steelscript.common.timeutils import (parse_timedelta, datetime_to_seconds,
                                          timedelta_total_seconds)
from steelscript.common.datastructures import RecursiveUpdateDict
from steelscript.common.exceptions import RvbdException, RvbdHTTPException

from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter
from steelscript.netprofiler.core._exceptions import ProfilerException
from steelscript.netprofiler.core._types import Column, ColumnContainer

__all__ = ['TrafficSummaryReport',
           'TrafficOverallTimeSeriesReport',
           'TrafficTimeSeriesReport',
           'TrafficFlowListReport',
           'HostTimeSeriesReport',
           'WANSummaryReport',
           'WANTimeSeriesReport',
           'IdentityReport']

logger = logging.getLogger(__name__)


class Query(object):
    """This class represents a netprofiler query instance.
    """
    def __init__(self, report, json, columns):
        self.report = report
        self.columns = columns
        self.id = json['id']
        self.actual_t0 = json['actual_t0']
        self.actual_t1 = json['actual_t1']

        # Collect the available columns
        acols = [acol for acol in json['columns'] if acol['available']]

        # find the columns in json which indicate they are 'available'
        # or have been computed as part of the request
        strict = report.strict_columns
        self.available_columns = self.report.profiler.get_columns(acols,
                                                                  strict=strict)
        if self.columns is None:
            self.columns = self.available_columns

        self.querydata = None
        self.data = None
        self.data_selected_columns = None

    def _select_columns(self, columns, ephemeral=True):
        """Return a set of column objects representing the requested columns."""

        avail_col_container = ColumnContainer(self.available_columns)

        # Selected columns as well as the argument columns may include
        # columns that are not listed as "available".  This is because
        # NetProfiler seems to not properly return all available columns
        # (For example, groupby=port lets you ask for the "protoport"
        # column id=18, but it is missing from available)
        #
        # However, ephemeral columns (like those for the
        # TrafficTimeSeriesReport) will only show up in the available
        # columns.  In this case we want to see if the the baseid
        # is in the requested set of columns, and if so add each
        # available column in it's place.
        #
        # For example, when a TrafficTimeSeriesReport is created, it takes
        # a time column (optionally) and one and only one value column.
        # Like:
        #
        # TrafficTimeSeriesReport.run(
        #     columns=[p.columns.key.time,
        #              p.columns.value.avg_bytes],
        #     query_columns_groupby="ports",
        #     query_columns=[{"name": "tcp/41017"},{"name":"udp/6343"}])
        #
        # The POST to NetProfiler will include only column 33 (avg_bytes),
        # because time is implied (don't ask...).
        #
        # Later when retrieving data via get_data(), the available_columns
        # will not include 33, but instead will include one ephemeral column
        # for each of the query_columns.  These are all going to be of type
        # strid="ID_AVG_BYTES", but the id will be some unknown large number
        # unique for each of tcp/4017 and udp/6343.
        #
        # But -- the caller of get_data() doesn't know the ephemeral ids,
        # they will likely just say "get me column 33", and this will
        # be translated to all available columns that have a *baseid* of 33.
        #
        # Process ephemeral columns
        baseids = set()
        ephemeral_cols = []
        for c in self.available_columns:
            if not c.ephemeral:
                continue

            if c.baseid != c.id:
                baseids.add(c.baseid)

            ephemeral_cols.append(c)

        res = []
        res_ids = []
        for col in columns:
            if type(col) is int or isinstance(col, types.StringTypes):
                # Either a number like 33 or name like 'avg_bytes'
                if col in avail_col_container:
                    # This column is in available
                    col = avail_col_container[col]
                elif col in self.report.profiler.columns:
                    # Not all columns show up in available, so check
                    # if it's a well-known column
                    col = self.report.profiler.columns[col]
                else:
                    raise ValueError(
                        'Invalid column for this report: %s' % col)
            elif type(col) is Column:
                # Already a Column object, just use it
                pass
            else:
                raise ValueError(
                    'Invalid column for this report: %s' % col)

            if col.id in baseids:
                # Don't ask for columns that were bases for other
                # ephemeral columns For example, user created the
                # report asking for col.id = 33 (avg_bytes).
                #
                # Later, the report available columns has:
                #    id=200000, baseid=33
                #    id=200001, baseid=33
                #
                continue

            res.append(col)
            res_ids.append(col.id)

        # Always add ephemeral columns
        res.extend([c for c in ephemeral_cols if c.id not in res_ids])

        return res

    def get_legend(self, columns=None):
        """Return the list columns associated with this query or by request."""

        if columns:
            return self._select_columns(columns)
        else:
            return self._select_columns(self.columns)

    def _to_native(self, row, columns):
        legend = self.get_legend(columns)
        for i, x in enumerate(row):
            try:
                if (legend[i].json['type'] == 'float' or
                    legend[i].json['type'] in 'reltime' or
                    legend[i].json['rate'] == 'opt'):
                    row[i] = float(x)
                elif legend[i].json['type'] == 'int':
                    row[i] = int(x)
            except ValueError:
                # netprofiler bug, %reduct columns labeled as ints
                # hostgroup "123:10" lableled as ints
                pass

        return row

    def _get_querydata(self, columns=None, limit=None):
        """Get the query data."""
        columns = self.get_legend(columns)

        # if we already got this data do not get it again
        changed = (self.data_selected_columns is None or
                   self.data_selected_columns != columns)
        if not changed:
            return

        params = {}

        if columns:
            params['columns'] = (','.join(str(col.id) for col in columns))

        if limit:
            params['limit'] = limit

        if not params:
            params = None
        self.querydata = self.report.profiler.api.report.queries(self.report.id,
                                                                 self.id,
                                                                 params=params)
        self.data = self.querydata['data']
        self.data_selected_columns = columns
        logger.debug(
            'Retrieved query data for '
            'query id {0} and column {1}'.format(self.id, columns))

    def get_iterdata(self, columns=None, limit=None):
        """Iterate over the query data."""
        self._get_querydata(columns, limit)
        for row in self.data:
            yield self._to_native(row, columns)

    def get_data(self, columns=None, limit=None):
        """Generate list from get_iterdata."""
        return list(self.get_iterdata(columns, limit))

    def get_totals(self, columns=None):
        """Return the totals associated with the requested columns."""
        self._get_querydata(columns)
        return self._to_native(self.querydata['totals'])

    def all_columns(self):
        """Returns all the columns available for this query.

        Used in conjunction with :py:meth:`Query.get_data` or
        :py:meth:`Query.get_iterdata` allows to retrieve all the data available
        for the query. Eg:

        query.get_iterdata(columns=query.all_columns())
        """
        return self.available_columns


class Report(object):
    """Base class for all NetProfiler reports.

    This class is normally not used directly, but instead via subclasses
    :class:`SingleQueryReport` and :class:`MultiQueryReport`.
    """

    RESOLUTION_MAP = {60: "1min",
                      60 * 15: "15min",
                      60 * 60: "hour",
                      60 * 60 * 6: "6hour",
                      60 * 60 * 24: "day",
                      60 * 60 * 24 * 7: "week"}

    # Note that report parameters such as the template id are not set
    # on initialization, but not until run().  This is to accommodate
    # a future load() command which will take a report id and load the
    # parameters of an existing report from NetProfiler.

    def __init__(self, profiler):
        """Initialize a report object.

        A report object is bound to an instance of a NetProfiler at creation.
        """

        self.profiler = profiler

        self.template_id = None
        self.timefilter = None
        self.resolution = None
        self.trafficexpr = None

        self.columns = None
        self.strict_columns = True  # ensure requested columns are validated

        self.query = None
        self.queries = list()

    def __enter__(self):
        return self

    def __exit__(self, instype, value, traceback):
        self.delete()

    def run(self, template_id, timefilter=None, resolution="auto",
            query=None, trafficexpr=None, data_filter=None, sync=True,
            custom_criteria=None):
        """Create the report and begin running the report on NetProfiler.

        If the `sync` option is True, periodically poll until the report is
        complete, otherwise return immediately.

        :param int template_id: numeric id of the template to use for the report

        :param timefilter: range of time to query,
            instance of :class:`TimeFilter`

        :param str resolution: data resolution, such as (1min, 15min, etc.),
             defaults to 'auto'

        :param str query: query object containing criteria

        :param trafficexpr: instance of :class:`TrafficFilter`

        :param str data_filter: deprecated filter to run against report data

        :param bool sync: if True, poll for status until the report is complete

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
        self.queries = list()
        self.last_status = None

        if resolution not in ["auto", "1min", "15min", "hour",
                              "6hour", "day", "week", "month"]:
            rd = parse_timedelta(resolution)
            resolution = self.RESOLUTION_MAP[int(timedelta_total_seconds(rd))]

        self.resolution = resolution

        start = datetime_to_seconds(self.timefilter.start)
        end = datetime_to_seconds(self.timefilter.end)

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

        if custom_criteria:
            for k, v in custom_criteria.iteritems():
                criteria[k] = v

        to_post = {"template_id": self.template_id,
                   "criteria": criteria}

        logger.debug("Posting JSON: %s" % to_post)

        response = self.profiler.api.report.reports(data=to_post)

        try:
            self.id = int(response['id'])
        except KeyError:
            raise ValueError(
                "failed to retrieve report id from report creation response: %s"
                % response)

        logger.info("Created report %d" % self.id)

        if sync:
            self.wait_for_complete()

    def wait_for_complete(self, interval=1, timeout=600):
        """Periodically checks report status and returns when 100% complete.
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

        - `status` indicating `completed` when finished
        - `percent` indicating the percentage complete (0-100)
        - `remaining_seconds` is an estimate of the time left until complete
        """
        if not self.id:
            return None

        self.last_status = self.profiler.api.report.status(self.id)

        return self.last_status

    def _load_queries(self, columns=None):
        if not self.id:
            raise ValueError("No id set, must run a report"
                             "or attach to an existing report first")

        data = self.profiler.api.report.queries(self.id)
        for json in data:
            self.queries.append(Query(self, json, columns))

        logger.debug("Report %d: loaded %d queries"
                     % (self.id, len(data)))

    def get_query_by_index(self, index=0):
        """Returns the query_id by specifying the index, defaults to 0."""
        if not self.id:
            raise ValueError("No id set, must run a report"
                             "or attach to an existing report first")

        if len(self.queries) == 0:
            self._load_queries(self.columns)

        query = self.queries[index]

        logger.debug("Retrieving query data for report %d, query %s" %
                     (self.id, query.id))

        return query

    def get_legend(self, index=0, columns=None):
        """Return legend describing the columns in this report.

        If `columns` is specified, restrict the legend to the list of
        requested columns.
        """
        query = self.get_query_by_index(index)
        return query.get_legend(columns)

    def get_iterdata(self, index=0, columns=None, limit=None):
        """Retrieve iterator for the result data.

        If `columns` is specified, restrict the legend to the list of
        requested columns.

        :param integer limit: Upper limit of rows of the result data.
        """
        query = self.get_query_by_index(index)
        return query.get_iterdata(columns, limit)

    def get_data(self, index=0, columns=None, limit=None):
        """Retrieve data for this report.

        If `columns` is specified, restrict the data to the list of
        requested columns.

        :param integer limit: Upper limit of rows of the result data.
        """
        query = self.get_query_by_index(index)
        return query.get_data(columns, limit)

    def get_totals(self, index=0, columns=None):
        """Retrieve the totals for this report.

        If `columns` is specified, restrict the totals to the list of
        requested columns.
        """
        query = self.get_query_by_index(index)
        return query.get_totals(columns)

    def delete(self):
        """Issue a call to NetProfiler delete this report."""
        try:
            self.profiler.api.report.delete(self.id)
        except:
            pass


class MultiQueryReport(Report):
    """Used to generate NetProfiler standard template reports."""

    def __init__(self, profiler):
        """Create a report using standard NetProfiler template ids which will
        include multiple queries, one for each widget on a report page.
        """
        super(MultiQueryReport, self).__init__(profiler)
        self.strict_columns = False

    def run(self, template_id, columns=None, timefilter=None, trafficexpr=None,
            data_filter=None, resolution="auto"):
        """The primary driver of these reports come from the `template_id` which
        defines the query sources.  Thus, no query input or
        realm/centricity/groupby keywords are necessary.

        :param int template_id: numeric id of the template to use for the report

        :param list columns: optional list of key and value columns to retrieve
            (use netprofiler.columns.*),  if omitted, will use template
            default columns instead.

        :param timefilter: range of time to query,
            instance of :class:`TimeFilter`

        :param trafficexpr: instance of :class:`TrafficFilter`

        :param str data_filter: deprecated filter to run against report data

        :param str resolution: data resolution, such as (1min, 15min, etc.),
             defaults to 'auto'
        """
        self.template_id = template_id
        self.columns = columns

        super(MultiQueryReport, self).run(template_id,
                                          timefilter=timefilter,
                                          resolution="auto",
                                          query=None,
                                          trafficexpr=trafficexpr,
                                          data_filter=data_filter,
                                          sync=True)

    def get_query_names(self):
        """Return full name of each query in report."""
        if not self.queries:
            self.get_data()
        return [q.id for q in self.queries]

    def get_data_by_name(self, query_name):
        """Return data and legend for query matching `query_name`."""
        for i, name in enumerate(self.get_query_names()):
            if name == query_name:
                legend = self.queries[i].get_legend()
                data = self.queries[i].get_data()
                return legend, data
        return None, None


class SingleQueryReport(Report):
    """Base class for NetProfiler REST API reports.

    This class is not normally instantiated directly.  See child classes such
    as :class:`TrafficSummaryReport`.
    """

    def __init__(self, profiler):
        super(SingleQueryReport, self).__init__(profiler)
        self._limit = None

    def run(self, realm,
            groupby="hos", columns=None, sort_col=None,
            timefilter=None, trafficexpr=None, host_group_type="ByLocation",
            resolution="auto", centricity="hos", area=None,
            data_filter=None, sync=True,
            query_columns_groupby=None, query_columns=None,
            limit=None, custom_criteria=None
            ):
        """
        :param str realm: type of query, this is automatically set by subclasses

        :param str groupby: sets the way in which data should be grouped
            (use netprofiler.groupby.*)

        :param list columns: list of key and value columns to retrieve
            (use netprofiler.columns.*)

        :param sort_col: :class:`Column` reference to sort by

        :param timefilter: range of time to query,
            instance of :class:`TimeFilter`

        :param trafficexpr: instance of :class:`TrafficFilter`

        :param str host_group_type: sets the host group type to use
            when the groupby is related to groups
            (such as 'group' or 'peer_group').

        :param str resolution: data resolution, such as (1min, 15min, etc.),
             defaults to 'auto'

        :param str centricity: 'hos' for host-based counts,
            or 'int' for interface based counts, only affects
            directional columns
        :type centricity: 'hos' or 'int'

        :param str area: sets the appropriate scope for the report

        :param str data_filter: deprecated filter to run against report data

        :param bool sync: if True, poll for status until the report is complete

        :param list query_columns_groupby: the groupby for time columns

        :param list query_columns: list of unique values associated with
            query_columns_groupby

        :param integer limit: Upper limit of rows of the result data.
            NetProfiler will return by default a maximum of 10,000 rows,
            but with this argument that limit can be raised up to '1000000',
            if needed.
        """

        # query related parameters
        self.realm = realm
        self.groupby = groupby or 'hos'
        self.columns = self.profiler.get_columns(columns, self.groupby)
        self.centricity = centricity
        self.host_group_type = host_group_type
        self.area = area

        query = {"realm": self.realm,
                 "centricity": self.centricity,
                 }

        if realm == 'traffic_time_series':
            # The traffic_time_series realm allows 1 and only 1
            # value column -- but the user may or may not want the time
            # column.  If the time column was specified, drop it from
            # what gets sent in the POST
            non_time_column = (
                list(set(self.columns) -
                     set([self.profiler.columns.key.time]))[0])
            query['columns'] = (
                [x.id for x in
                 self.profiler.get_columns([non_time_column], self.groupby)])
        else:
            query['columns'] = [col.id for col in self.columns]

        if self.groupby is not None:
            query["group_by"] = self.groupby

        if sort_col:
            self.sort_col = self.profiler.get_columns([sort_col], self.groupby)[0]
        else:
            self.sort_col = None

        if self.sort_col is not None:
            query["sort_column"] = self.sort_col.id

        if self.area is not None:
            query['area'] = self.profiler._parse_area(self.area)

        if self.groupby in ['gro', 'gpp', 'gpr', 'pgp', 'pgr']:
            query['host_group_type'] = self.host_group_type

        if query_columns_groupby is not None:
            query[query_columns_groupby] = query_columns
            query['host_group_type'] = self.host_group_type

        self._limit = limit
        if limit is not None:
            if (APIVersion("1.4") not in self.profiler.supported_versions):
                raise ProfilerException(
                    "'limit' not supported by this NetProfiler API version")

            elif realm.endswith('time_series'):
                raise ProfilerException("'limit' option is not allowed in "
                                        "time series report")

            query['limit'] = limit
        super(SingleQueryReport, self).run(template_id=184,
                                           timefilter=timefilter,
                                           resolution=resolution,
                                           query=query,
                                           trafficexpr=trafficexpr,
                                           data_filter=data_filter,
                                           sync=sync,
                                           custom_criteria=custom_criteria)

    def _load_queries(self, columns=None):
        super(SingleQueryReport, self)._load_queries(columns)

    def get_legend(self, columns=None):
        return super(SingleQueryReport, self).get_legend(0, columns)

    def get_iterdata(self, columns=None, limit=None):
        return super(SingleQueryReport, self).get_iterdata(
            0, columns, limit or self._limit)

    def get_data(self, columns=None, limit=None):
        return super(SingleQueryReport, self).get_data(
            0, columns, limit or self._limit)


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
            resolution="auto", centricity="hos", area=None, sync=True,
            limit=None):
        """See :meth:`SingleQueryReport.run` for a description of the keyword
        arguments.
        """
        return super(TrafficSummaryReport, self).run(
            realm='traffic_summary',
            groupby=groupby, columns=columns, sort_col=sort_col,
            timefilter=timefilter, trafficexpr=trafficexpr,
            host_group_type=host_group_type, resolution=resolution,
            centricity=centricity, area=area, sync=sync, limit=limit)


class TrafficOverallTimeSeriesReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create an overall time series report."""
        super(TrafficOverallTimeSeriesReport, self).__init__(profiler)

    def run(self, columns,
            timefilter=None, trafficexpr=None,
            resolution="auto", centricity="hos", area=None, sync=True):
        """See :meth:`SingleQueryReport.run` for a description of the keyword
        arguments.

        Note that `sort_col`, `groupby`, and `host_group_type` are not
        applicable to this report type.
        """
        return super(TrafficOverallTimeSeriesReport, self).run(
            realm='traffic_overall_time_series',
            groupby='tim', columns=columns, sort_col=None,
            timefilter=timefilter, trafficexpr=trafficexpr,
            host_group_type=None, resolution=resolution,
            centricity=centricity, area=area, sync=sync)


class TrafficTimeSeriesReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create a top-N style time series report."""
        super(TrafficTimeSeriesReport, self).__init__(profiler)

    def run(self, columns, query_columns_groupby, query_columns,
            timefilter=None, trafficexpr=None, host_group_type=None,
            resolution="auto", centricity="hos", area=None, sync=True,
            custom_criteria=None):
        """
        :param str query_columns_groupby: defines the type of data for
            each unique column

        :param list query_columns: list of expressions that define each
            column.  The specific format of each expression depends
            on `query_columns_groupby`.

        See :meth:`SingleQueryReport.run` for a description of the rest
        of the possible parameters.

        Note that `sort_col`, `groupby`, are not applicable to this
        report type.  `host_group_type` only applies if `query_columns_groupby`
        is `host_groups`.

        """

        if len(set(columns) - {self.profiler.columns.key.time, 'time'}) != 1:
            raise ValueError("Columns must be a list of only one column "
                             "for this type of report")

        try:
            return super(TrafficTimeSeriesReport, self).run(
                realm='traffic_time_series',
                groupby='tim', columns=columns, sort_col=None,
                timefilter=timefilter, trafficexpr=trafficexpr,
                host_group_type=host_group_type,
                resolution=resolution, centricity=centricity,
                area=area, sync=sync,
                query_columns_groupby=query_columns_groupby,
                query_columns=query_columns,
                custom_criteria=custom_criteria)
        except RvbdHTTPException as e:
            if 'Error creating element ports' in str(e):
                raise ProfilerException(
                    "TrafficTimeSeriesReport using 'ports' not "
                    "supported by this NetProfiler software version")
            raise


class HostTimeSeriesReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create a Total Hosts Over Time report."""
        super(HostTimeSeriesReport, self).__init__(profiler)

    def run(self, timefilter=None, trafficexpr=None,
            resolution="auto", sync=True):
        """
        See :meth:`SingleQueryReport.run` for a description of the rest
        of the possible parameters.

        Note this report does not allow columns to be chosen,
        the data response will include time and total hosts seen:
            Key('time')
            Value('total_hosts_network_stats')

        """
        columns = [self.profiler.columns.key.time,
                   self.profiler.columns.value.total_hosts_network_stats]

        return super(HostTimeSeriesReport, self).run(
            realm='hosts_time_series',
            groupby='tim', columns=columns, sort_col=None,
            timefilter=timefilter, trafficexpr=trafficexpr,
            resolution=resolution, centricity='hos',
            sync=sync)


class TrafficFlowListReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create a flow list report."""
        super(TrafficFlowListReport, self).__init__(profiler)

    def run(self, columns, sort_col=None,
            timefilter=None, trafficexpr=None, sync=True, limit=None):
        """See :meth:`SingleQueryReport.run` for a description of the keyword
        arguments.

        Note that only `columns, `sort_col`, `timefilter`, `trafficexpr` and
        `limit` apply to this report type.
        """
        return super(TrafficFlowListReport, self).run(
            realm='traffic_flow_list',
            groupby='hos', columns=columns, sort_col=sort_col,
            timefilter=timefilter, trafficexpr=trafficexpr, host_group_type=None,
            centricity="hos", area=None, sync=sync,
            limit=limit)


class WANReport(SingleQueryReport):
    """ Base class for WAN Report Types, use subclasses for report generation
    """
    def __init__(self, profiler):
        """ Create a WAN Traffic Summary report """
        super(WANReport, self).__init__(profiler)

        # cache data for quick calculations in opposite direction
        self._timefilter = None
        self._columns = None
        self._wan_data = None
        self._lan_data = None

        # report parameters
        self.realm = None
        self.centricity = None
        self.groupby = None
        self.columns = None
        self.timefilter = None
        self.trafficexpr = None
        self.resolution = 'auto'

        # data parameters
        self.table = None

    def get_legend(self):
        header = self.table.index.names
        header.extend(list(self.table.columns))
        return header

    def get_interfaces(self, device_ip):
        """ Query netprofiler to attempt to automatically determine
            LAN and WAN interface ids.
        """
        cols = self.profiler.get_columns(['interface_dns', 'interface'])
        super(WANReport, self).run(realm='traffic_summary',
                                   groupby='ifc',
                                   columns=cols,
                                   timefilter=TimeFilter.parse_range('last 1 h'),
                                   trafficexpr=TrafficFilter('device %s' % device_ip),
                                   centricity='int',
                                   resolution='auto',
                                   sync=True)
        interfaces = self._get_data()

        lan = [address for name, address in interfaces if 'lan' in name]
        wan = [address for name, address in interfaces if 'wan' in name]

        if not lan or not wan:
            raise RvbdException('Unable to determine LAN and WAN interfaces for device %s' %
                                device_ip)
        return lan, wan

    def get_data(self, as_list=True, calc_reduction=False, calc_percentage=False):
        """Retrieve WAN report data.

        :param bool as_list: return list of lists or pandas DataFrame
        :param bool calc_reduction: include extra column with optimization
            reductions
        :param bool calc_percentage: include extra column with optimization
            percent reductions
        """
        def reduction(x, y):
            return x - y
        def percentage(x, y):
            return (x - y * 1.0) / x

        if calc_reduction or calc_percentage:
            pairs = []
            s = set(self.table.columns)
            for i in s:
                if i.startswith('LAN_') and i.replace('LAN_', 'WAN_') in s:
                    pairs.append((i, i.replace('LAN_', 'WAN_')))

            for lan_col, wan_col in pairs:
                lan = self.table[lan_col]
                wan = self.table[wan_col]

                if calc_reduction:
                    name = '%s_reduct' % lan_col.lstrip('LAN_')
                    self.table[name] = reduction(lan, wan)
                if calc_percentage:
                    name = '%s_reduct_pct' % lan_col.lstrip('LAN_')
                    self.table[name] = percentage(lan, wan)

        if as_list:
            # convert to CSV and parse that into list
            f = StringIO.StringIO()
            self.table.to_csv(f, header=False)
            return [x.split(',') for x in f.getvalue().splitlines()]
        else:
            return self.table

    def _align_columns(self, direction, df_lan, df_wan):
        """Replace lan and wan dataframe columns with those appropriate for
        inbound/outbound data.
        """
        # To help illustrate, column prefixes are as follows:
        #
        #               LAN         WAN
        #   Inbound     <out_>      <in_>
        #   Outbound    <in_>       <out_>

        # create boolean lists for in, out, and universal columns
        in_flags = [c.startswith('in_') for c in df_lan.keys()]
        out_flags = [c.startswith('out_') for c in df_lan.keys()]
        key_flags = [not x and not y for x, y in zip(in_flags, out_flags)]

        if direction == 'inbound':
            lan_flags = [x or y for x, y in zip(key_flags, out_flags)]
            lan_columns = df_lan.ix[:, lan_flags]
            lan_columns.rename(columns=lambda n: n.replace('out_', 'LAN_'), inplace=True)
            wan_columns = df_wan.ix[:, in_flags]
            wan_columns.rename(columns=lambda n: n.replace('in_', 'WAN_'), inplace=True)
        elif direction == 'outbound':
            lan_flags = [x or y for x, y in zip(key_flags, in_flags)]
            lan_columns = df_lan.ix[:, lan_flags]
            lan_columns.rename(columns=lambda n: n.replace('in_', 'LAN_'), inplace=True)
            wan_columns = df_wan.ix[:, out_flags]
            wan_columns.rename(columns=lambda n: n.replace('out_', 'WAN_'), inplace=True)
        else:
            raise RvbdException('Invalid direction %s for WANSummaryReport' % direction)

        return lan_columns, wan_columns

    def _convert_columns(self):
        """Replace columns with in/out variants if available."""
        result = []
        seen = set()
        available = self.profiler.search_columns([self.realm],
                                                 [self.centricity],
                                                 [self.groupby])
        keys = set(a.key for a in available)

        self.columns = self.profiler.get_columns(self.columns)

        for c in self.columns:
            # normalize the name
            if c.key.startswith('in_') or c.key.startswith('out_'):
                key = c.key.split('_', 1)[1]
            else:
                key = c.key

            if key not in seen:
                seen.add(key)

                in_key = 'in_%s' % key
                out_key = 'out_%s' % key

                # find matches
                if in_key in keys and out_key in keys:
                    result.extend(self.profiler.get_columns([in_key, out_key]))
                else:
                    # e.g. 'interface', but not 'in_avg_bytes'
                    result.append(c)

        self.columns = result

    def _get_data(self):
        """Normal get_data, used internally."""
        return super(WANReport, self).get_data()

    def _run_reports(self, lan_interfaces, wan_interfaces):
        """Verify cache and run reports for both interfaces."""

        if not (self._timefilter and self._timefilter == self.timefilter and
                self._columns == self.columns):

            # store for cache verification later
            self._timefilter = self.timefilter
            self._columns = self.columns

            # fetch data for both interfaces
            self._run(wan_interfaces)
            self._wan_data = self._get_data()
            self._run(lan_interfaces)
            self._lan_data = self._get_data()

        return self._lan_data, self._wan_data

    def _run(self, interfaces):
        """Internal run method, calls super with class attributes."""
        return super(WANReport, self).run(realm=self.realm,
                                          groupby=self.groupby,
                                          columns=self.columns,
                                          timefilter=self.timefilter,
                                          trafficexpr=self.trafficexpr,
                                          centricity=self.centricity,
                                          resolution=self.resolution,
                                          data_filter=('interfaces_a', ','.join(interfaces)),
                                          sync=True)

    def run(self, **kwargs):
        """Unimplemented for subclass to override."""
        pass


class WANSummaryReport(WANReport):
    """Tabular or summary WAN Report data."""
    def __init__(self, profiler):
        """ Create a WAN Traffic Summary report """
        super(WANSummaryReport, self).__init__(profiler)
        self._configure()

    def _configure(self):
        # setup summary parameters
        self.realm = 'traffic_summary'
        self.centricity = 'int'

    def run(self, lan_interfaces, wan_interfaces, direction,
            columns=None, timefilter='last 1 h', trafficexpr=None,
            groupby='ifc', resolution='auto'):
        """Run WAN Report.

        :param lan_interfaces: list of full interface name for LAN
            interface, e.g. ['10.99.16.252:1']
        :param wan_interfaces: list of full interface name for WAN interface
        :param direction:
        :type direction: 'inbound' or 'outbound'
        :param columns: list of columns available in both 'in' and 'out'
            versions, for example, ['avg_bytes', 'total_bytes'], instead of
            ['in_avg_bytes', 'out_avg_bytes']
        """
        # we need some heavier data analysis tools for this report
        import pandas as pd

        self.groupby = groupby
        self.columns = columns
        self.timefilter = timefilter
        self.trafficexpr = trafficexpr
        self.resolution = resolution

        self._configure()
        self._convert_columns()

        lan_data, wan_data = self._run_reports(lan_interfaces, wan_interfaces)

        key_columns = [c for c in self.columns if c.iskey]

        # create data frames
        df_lan = pd.DataFrame.from_records(lan_data, columns=[c.key for c in self.columns])
        df_lan.set_index([c.key for c in key_columns], inplace=True)

        df_wan = pd.DataFrame.from_records(wan_data, columns=[c.key for c in self.columns])
        df_wan.set_index([c.key for c in key_columns], inplace=True)

        # remove and rename columns appropriately
        lan_columns, wan_columns = self._align_columns(direction, df_lan, df_wan)

        self.table = lan_columns.join(wan_columns, how='inner')


class WANTimeSeriesReport(WANReport):
    """
    """
    def __init__(self, profiler):
        """Create a WAN Time Series report."""
        super(WANTimeSeriesReport, self).__init__(profiler)
        self._configure()

    def _configure(self):
        # setup summary parameters
        self.realm = 'traffic_overall_time_series'
        self.centricity = 'int'
        self.groupby = 'tim'

    def run(self, lan_interfaces, wan_interfaces, direction,
            columns=None, timefilter='last 1 h', trafficexpr=None,
            groupby=None, resolution='auto'):
        """ Run WAN Time Series Report

        :param lan_interfaces: list of full interface name for LAN
            interface, e.g. ['10.99.16.252:1']

        :param wan_interfaces: list of full interface name for WAN interface

        :param direction:
        :type direction: 'inbound' or 'outbound'

        :param columns: list of columns available in both `in_` and `out_`
            versions, for example, ['avg_bytes', 'total_bytes'], instead of
            ['in_avg_bytes', 'out_avg_bytes']

        :param str groupby: Ignored for this report type, included for
            interface compatibility
        """
        # we need some heavier data analysis tools for this report
        import pandas as pd

        self.columns = columns
        self.timefilter = timefilter
        self.trafficexpr = trafficexpr
        self.resolution = resolution
        self.groupby = 'tim'

        self._configure()
        self._convert_columns()

        lan_data, wan_data = self._run_reports(lan_interfaces, wan_interfaces)

        key_columns = [c.key for c in self.columns if c.iskey]
        if key_columns[0] != 'time':
            raise RvbdException('Invalid Key Column for WANTimeSeriesReport')

        labels = [c.key for c in self.columns]

        # create data frames, and convert timestamps
        df_lan = pd.DataFrame.from_records(lan_data, columns=labels)
        df_lan.set_index('time', inplace=True)
        df_lan.index = df_lan.index.map(int).astype('M8[s]')

        df_wan = pd.DataFrame.from_records(wan_data, columns=labels)
        df_wan.set_index('time', inplace=True)
        df_wan.index = df_wan.index.map(int).astype('M8[s]')

        # remove and rename columns appropriately
        lan_columns, wan_columns = self._align_columns(direction, df_lan, df_wan)

        self.table = lan_columns.join(wan_columns, how='inner')

    def get_data(self, as_list=True):
        """Retrieve WAN report data as list of lists or pandas DataFrame.

        If `as_list` is True, return list of lists, False will return
        pandas DataFrame.
        """
        return super(WANTimeSeriesReport, self).get_data(as_list=as_list,
                                                         calc_reduction=False,
                                                         calc_percentage=False)


class IdentityReport(SingleQueryReport):
    """
    """
    def __init__(self, profiler):
        """Create a report for Active Directory events."""
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

    def run(self, username=None, timefilter=None, trafficexpr=None, sync=True,
            limit=None):
        """Run complete user identity report over the requested timeframe.

        `username` specific id to filter results by

        `timefilter` is the range of time to query, a TimeFilter object

        `trafficexpr` is an optional TrafficFilter object

        :param integer limit: Upper limit of rows of the result data
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
            sync=sync,
            limit=limit
        )

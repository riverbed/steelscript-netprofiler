# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.



"""
This module contains the NetProfiler class, which is the main interface to
a SteelCentral NetProfiler appliance. It allows, among other things, retrieving
the state of the NetProfiler, modifying its settings and performing operations
like creating running reports.
"""

import types
import logging
import itertools

from steelscript.common.utils import DictObject
from steelscript.common.api_helpers import APIVersion
from steelscript.netprofiler.core import _api1
from steelscript.netprofiler.core import _constants
from steelscript.common._fs import SteelScriptDir
from steelscript.netprofiler.core._types import Column, AreaContainer, ColumnContainer
from steelscript.common.exceptions import RvbdException

import steelscript.common.service

__all__ = ['NetProfiler']

API_VERSIONS = ["1.0"]

logger = logging.getLogger(__name__)


def make_hash(realm, centricity, groupby):
    return realm + centricity + groupby


class NetProfiler(steelscript.common.service.Service):
    """The NetProfiler class is the main interface to interact with a
    NetProfiler appliance.  Primarily this provides an interface to reporting.
    """

    def __init__(self, host, port=None, auth=None):
        """Establishes a connection to a NetProfiler appliance.

        :param str host: name or IP address of the NetProfiler to
            connect to

        :param int port: TCP port on which the NetProfiler appliance
            listens.  If this parameter is not specified, the function will try
            to automatically determine the port.

        :param auth: defines the authentication method and credentials
            to use to access the NetProfiler.  It should be an instance of
            :py:class:`UserAuth<steelscript.common.service.UserAuth>` or
            :py:class:`OAuth<steelscript.common.service.OAuth>`

        :param str force_version: API version to use when communicating.
            if unspecified, this will use the latest version supported by both
            this implementation and the NetProfiler appliance.

        See the base :py:class:`Service<steelscript.common.service.Service>` class
        for more information about additional functionality supported.
        """
        super(NetProfiler, self).__init__("profiler", host, port,
                                          auth=auth,
                                          versions=[APIVersion("1.0")])

        self.api = _api1.Handler(self)

        self.groupbys = DictObject.create_from_dict(_constants.groupbys)
        self.realms = _constants.realms
        self.centricities = _constants.centricities

        self._info = None

        self._load_file_caches()
        self.columns = ColumnContainer(self._unique_columns())
        self.areas = AreaContainer(self._areas_dict.iteritems())

    def _load_file_caches(self):
        """Load and unroll locally cached files

        We want to avoid making any calls for column data here
        and just load what has been stored locally for now
        """
        self._fs_data = SteelScriptDir('NetProfiler', 'data')

        columns_filename = 'columns-' + self.version + '.pcl'
        self._columns_file = self._fs_data.get_data(columns_filename)
        if self._columns_file.data is None:
            self._columns_file.data = dict()

        areas_filename = 'areas-' + self.version + '.json'
        self._areas_file = self._fs_data.get_config(areas_filename)
        if self._areas_file.data is None:
            self._areas_file.data = self.api.report.areas()
            self._areas_file.write()

        self._verify_cache()
        self._areas_dict = dict(self._genareas(self._areas_file.data))

    def _verify_cache(self, refetch=False):
        """Retrieve all the possible combinations of
        groupby, centricity and realm using the rule shown under
        the search_columns method.

        By default, all these permutations will be checked against
        the current local cache file, and any missing keys will be
        retrieved from the server.

        :param bool refetch: will force an api refresh call from the
            machine even if the data can be found in local cache.
        """
        columns = list()
        write = False
        for realm in self.realms:
            if realm == 'traffic_flow_list' or realm == 'identity_list':
                centricities = ['hos']
            else:
                centricities = self.centricities

            for centricity in centricities:
                if realm == 'traffic_summary':
                    groupbys = [x for x in self.groupbys.values() if x != 'thu']
                elif realm == 'traffic_overall_time_series':
                    groupbys = ['tim']
                elif realm == 'identity_list':
                    groupbys = ['thu']
                else:
                    groupbys = ['hos']

                for groupby in groupbys:
                    _hash = make_hash(realm, centricity, groupby)
                    if refetch or _hash not in self._columns_file.data:
                        logger.debug('Requesting columns for triplet: '
                                     '%s, %s, %s' % (realm, centricity, groupby))
                        api_call = self.api.report.columns(realm,
                                                           centricity, groupby)
                        # generate Column objects from json
                        api_columns = self._gencolumns(api_call)
                        # compare against objects we've already retrieved
                        existing = [c for c in columns if c in api_columns]
                        new_columns = [c for c in api_columns if c not in existing]
                        columns.extend(new_columns)

                        # add them to data, preserving existing objects
                        self._columns_file.data[_hash] = existing + new_columns
                        write = True
        if write:
            self._columns_file.write()

    def _unique_columns(self):
        """Pull unique columns from _columns_file (a dict of lists). """
        def unique(seq):
            seen = set()
            for lst in seq:
                for c in lst:
                    if c in seen:
                        continue
                    seen.add(c)
                    yield c
        return list(unique(self._columns_file.data.values()))

    def _parse_area(self, area):
        if isinstance(area, types.StringTypes):
            if area not in self._areas_dict:
                raise ValueError('{0} is not a valid area type for this'
                                 'netprofiler'.format(area))
            return self._areas_dict[area]

    def _gencolumns(self, columns):
        """Return a list of Column objects from a list of json columns. """
        res = []
        for c in columns:
            key = c['strid'].lower()[3:]
            res.append(Column(c['id'], key, c['name'], json=c))
        return res

    def _genareas(self, areas):
        res = list()
        for area in areas:
            res.append((area['name'].replace(' ', '_'), area['id']))
        return res

    def _fetch_info(self):
        if self._info is None:
            self._info = self.api.common.info()

    @property
    def version(self):
        """Returns the software version of the NetProfiler"""
        self._fetch_info()
        return self._info['sw_version']

    def get_columns(self, columns, groupby=None):
        """Return valid Column objects for list of columns

        :param list columns: list of strings and/or Column objects

        :param str groupby: will optionally ensure that the selected columns
            are valid for the given groupby
        """
        res = list()
        if groupby:
            groupby_cols = self.search_columns(groupbys=[groupby])
        else:
            groupby_cols = None

        colnames = set(c.key for c in self.columns)

        for column in columns:
            if isinstance(column, types.StringTypes):
                cname = column
            else:
                try:
                    # usually a Column class
                    cname = column.key
                except AttributeError:
                    # likely json-dict
                    cname = column['strid'].lower()[3:]

            if cname not in colnames:
                raise RvbdException('{0} is not a valid column '
                                    'for this netprofiler'.format(column))
            if groupby_cols and cname not in groupby_cols:
                raise RvbdException('{0} is not a valid column '
                                    'for groupby {1}'.format(column, groupby))
            res.append(self.columns[cname])

        return res

    def get_columns_by_ids(self, ids):
        """Return Column objects that have ids in list of strings `ids`.

        :param list ids: list of integer ids
        """
        res = [self.columns[i] for i in ids]
        return res

    def search_columns(self, realms=None, centricities=None, groupbys=None):
        """Identify columns given one or more values for the triplet.

        :param list realms: list of strings
        :param list centricities: list of strings
        :param list groupbys: list of strings

        Results will be based on the following relationship table:

        ============================= ============ ==================
        realm                         centricity   groupby
        ============================= ============ ==================
        traffic_summary               hos,int      all (except thu)
        traffic_overall_time_series   hos,int      tim
        traffic_flow_list             hos          hos
        identity_list                 hos          thu
        ============================= ============ ==================

        """
        result = set()

        if realms is None:
            realms = self.realms
        if centricities is None:
            centricities = self.centricities
        if groupbys is None:
            groupbys = self.groupbys.values()

        datakeys = self._columns_file.data.keys()
        search_keys = [make_hash(*p) for p in itertools.product(realms,
                                                                centricities,
                                                                groupbys)]

        keys = [k for k in datakeys if k in search_keys]
        for key in keys:
            result.update(x for x in self._columns_file.data[key])
        return list(result)

    def logout(self):
        """ Issue logout command to netprofiler machine. """
        if self.conn:
            try:
                self.api.common.logout()
            except AttributeError:
                pass
            super(NetProfiler, self).logout()

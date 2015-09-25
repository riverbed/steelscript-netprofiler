# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.common.api_helpers import APIVersion


class APIGroup(object):
    """Wrapper for API functions
    """
    def __init__(self, uri_prefix, service):
        self.uri_prefix = uri_prefix
        self.service = service


class API1Group(APIGroup):
    def _json_request(self, urlpath, method='GET', data=None, params=None):
        """Issue the given API request via JSON
        """
        return self.service.conn.json_request(method, self.uri_prefix + urlpath,
                                              body=data, params=params)


class Common(API1Group):
    def __init__(self, *args, **kwargs):
        super(Common, self).__init__(*args, **kwargs)

    def info(self):
        return self._json_request('/info.json')

    def logout(self):
        return self._json_request('/logout.json')


class Report(API1Group):
    def __init__(self, *args, **kwargs):
        super(Report, self).__init__(*args, **kwargs)
        self.columns_cache = dict()
        self.realms_cache = None
        self.centricities_cache = None
        self.groupbys_cache = None
        self.areas_cache = None

    def realms(self, force=False):
        if not self.realms_cache or force:
            self.realms_cache = self._json_request('/realms.json')
        return self.realms_cache

    def centricities(self, force=False):
        if not self.centricities_cache or force:
            self.centricities_cache = self._json_request('/centricities.json')
        return self.centricities_cache

    def groupbys(self, force=False):
        if not self.groupbys_cache or force:
            self.groupbys_cache = self._json_request('/group_bys.json')
        return self.groupbys_cache

    def columns(self, realm, centricity, group_by, force=False):
        params = {}
        params['group_by'] = group_by
        params['centricity'] = centricity
        params['realm'] = realm
        key = str(realm) + str(centricity) + str(group_by)
        if key not in self.columns_cache or force:
            self.columns_cache[key] = self._json_request('/columns.json',
                                                         params=params)
        return self.columns_cache[key]

    def areas(self, force=False):
        if not self.areas_cache or force:
            self.areas_cache = self._json_request('/areas.json')
        return self.areas_cache

    def reports(self, data, params=None):
        return self._json_request('/reports', method='POST',
                                  data=data, params=params)

    def status(self, rid):
        return self._json_request('/reports/{0}.json'.format(rid))

    def queries(self, rid, qid=None, params=None):
        uri = '/reports/{0}/queries'.format(rid)
        if qid is not None:
            uri += '/' + str(qid)
        uri += '.json'
        return self._json_request(uri, params=params)

    def delete(self, rid):
        return self._json_request('/reports/{0}.json'.format(rid),
                                  method='DELETE')


class Devices(API1Group):
    def __init__(self, *args, **kwargs):
        super(Devices, self).__init__(*args, **kwargs)
        self.device_cache = None        # currently unused
        self.type_cache = None

    def get_all(self, typeid=None, cidr=None, force=False):
        """ Get list of all devices with optional typeid and cidr filtering
        """
        params = {}
        if typeid:
            params['type_id'] = typeid
        if cidr:
            params['cidr'] = cidr
        return self._json_request('', params=params)

    def get_details(self, ipaddr):
        """ Retrieve device instance for a given ip address
        """
        return self._json_request('/{0}.json'.format(str(ipaddr)))

    def get_types(self, force=False):
        """ Get list of unique (type_id, type) pairs for known devices
        """
        if not self.type_cache or force:
            data = self.get_all()
            types = set((x['type_id'], x['type']) for x in data)
            self.type_cache = list(types)
            self.type_cache.sort(key=lambda x: x[0])
        return self.type_cache


class HostGroupTypes(API1Group):
    def __init__(self, *args, **kwargs):
        super(HostGroupTypes, self).__init__(*args, **kwargs)
        self.device_cache = None        # currently unused
        self.type_cache = None

    def get_all(self, favorite=None, offset=None, sortby=None,
                sort=None, type=None, limit=None):
        """ Get a list of all host grouping types
        """
        params = {}
        if favorite:
            params['favorite'] = favorite
        if offset:
            params['offset'] = offset
        if sortby:
            params['sortby'] = sortby
        if sort:
            params['sort'] = sort
        if type:
            params['type'] = type
        if limit:
            params['limit'] = limit
        return self._json_request('', params=params)

    def get_all_groups(self, type_id, offset=None, sortby=None,
                       sort=None, limit=None):
        """ Get a list of all host groups for a given host grouping type
        """
        params = {}
        if offset:
            params['offset'] = offset
        if sortby:
            params['sortby'] = sortby
        if sort:
            params['sort'] = sort
        if limit:
            params['limit'] = limit
        return self._json_request('/{0}/groups'.format(str(type_id)),
                                  params=params)

    def get_config(self, type_id):
        """ Get host grouping type configuration
        """
        params = {}
        return self._json_request('/{0}/config'.format(str(type_id)),
                                  params=params)

    def get(self, type_id):
        """ Get a specific group type element
        """
        params = {}
        return self._json_request('/{0}'.format(str(type_id)), params=params)

    def get_group(self, type_id, group_id):
        """ Get a specific group type element
        """
        params = {}
        return self._json_request('/{0}/groups/{1}'
                                  .format(str(type_id), str(group_id)),
                                  params=params)

    def get_group_members(self, type_id, group_id,
                          offset=None, sort=None,limit=None):
        """ Get a list of hosts in a specified host group
        """
        params = {}
        if offset:
            params['offset'] = offset
        if sort:
            params['sort'] = sort
        if limit:
            params['limit'] = limit
        return self._json_request('/{0}/groups/{1}/members'
                                  .format(str(type_id), str(group_id)),
                                  params=params)

    def create(self, name, desc, favorite, config):
        """ Create a new host grouping type
        """
        params = {}
        data = {}
        data['name'] = name
        data['description'] = desc
        data['favorite'] = favorite
        data['config'] = config
        return self._json_request('', method='POST', data=data, params=params)

    def set_config(self, type_id, config):
        """ Update host grouping type configuration
        """
        params = {}
        return self._json_request('/{0}/config'.format(str(type_id)),
                                  method='PUT', data=config, params=params)

    def set(self, type_id, name, desc, favorite, config):
        """ Update one host grouping type
        """
        params = {}
        data = {}
        data['name'] = name
        data['description'] = desc
        data['favorite'] = favorite
        data['config'] = config
        return self._json_request('/{0}'.format(str(type_id)),
                                  method='PUT', data=data, params=params)

    def delete(self, type_id):
        """ Delete one host grouping type
        """
        params = {}
        return self._json_request('/{0}'.format(str(type_id)),
                                  method='DELETE', params=params)


class Services(API1Group):

    def get_all(self):
        """ Return a list of all services. """
        return self._json_request('')


class Handler(object):
    def __init__(self, profiler):
        self.report = Report('/api/profiler/1.0/reporting', profiler)
        self.devices = Devices('/api/profiler/1.0/devices', profiler)
        self.common = Common('/api/common/1.0', profiler)

        if profiler.supports_version('1.2'):
            self.host_group_types = HostGroupTypes(
                '/api/profiler/1.2/host_group_types', profiler)

        if profiler.supports_version('1.3'):
            self.services = Services(
                '/api/profiler/1.3/services', profiler)

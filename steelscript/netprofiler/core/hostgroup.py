# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from steelscript.common.exceptions import RvbdException, RvbdHTTPException
import logging

# Examples:
#
# >>> byloc = HostGroupType.find_by_name(netprofiler, 'ByLocation')
#
# >>> byloc.group['sanfran']
# <HostGroup 'sanfran'>
#
# >>> byloc.group['sanfran'].get()
#   ['10.99.1/24']
#
#   >>> byloc.group['sanfran'].add('10.99.2/24')
#   ['10.99.1/24', '10.99.2/24']
#
#   >>> byloc.save()
#

logger = logging.getLogger(__name__)


class HostGroupType(object):
    def __init__(self, netprofiler, id):
        # Host group id
        self.id = id
        # NetProfiler
        self.netprofiler = netprofiler

        # Properties filled in by load or by create
        self.name = ""
        self.favorite = ""
        self.description = ""

        # Array of cidr/name config items
        self.config = []

        # Dictionary of HostGroup entries by name
        self.groups = {}

    @classmethod
    def find_by_name(cls, netprofiler, name):
        """Find and load a host group type by name."""
        type_id = HostGroupType._find_id(netprofiler, name)
        host_group_type = HostGroupType(netprofiler, type_id)
        host_group_type.load()
        return host_group_type

    @classmethod
    def create(cls, netprofiler, name, favorite=False, description=''):
        """Create a new hostgroup type.

        The new host group type will be created on the NetProfiler
        when save() is called.

        """
        # host_group_type.id is set to None until it gets saved
        host_group_type = HostGroupType(netprofiler, None)
        host_group_type.name = name
        host_group_type.favorite = favorite
        host_group_type.description = description
        return host_group_type

    def load(self):
        """Load settings and groups."""
        if self.id is None:
            raise RvbdException('Type: "{0}" has not yet been saved to the '
                                'Netprofiler, so there is nothing to load. '
                                'Call $host_group_type.save() first to save it.'
                                .format(self.name))
        info = self.netprofiler.api.host_group_types.get(self.id)
        self.name = info['name']
        self.favorite = info['favorite']
        self.description = info['description']

        try:
            self.config = self.netprofiler.api.host_group_types.get_config(self.id)
        except RvbdHTTPException as e:
            # When you call get_config a RESOURCE_NOT_FOUND error is raised if
            # the config of that type is empty, even if the host group type
            # exists. Because of this we except that error and move on with load
            if e.error_id == 'RESOURCE_NOT_FOUND':
                logger.debug('RESOURCE_NOT_FOUND exception raised because the '
                             'config is empty. It was excepted because we '
                             'still want the HostGroupType.')
                self.config = []
                self.groups = []
            else:
                raise e

        # Get the groups, we will need to reformat the output to fit our dict.
        for host_group in self.config:
            self.groups[host_group['name']] = HostGroup(self, host_group['name'])

    def save(self):
        """Save settings and groups.

        If this is a new host group type, it will be created.
        """

        # If this is a new HostGroupType, then create it
        if self.id is None:
            type_info = self.netprofiler.api.host_group_types.create(
                self.name, self.description, self.favorite, self.config)
            self.id = type_info['id']
            logger.debug("New HostGroupType created with Name: {0} and ID: {1}"
                         .format(self.name, self.id))
            return
        # Otherwise just set the preexisting HostGroupType with the new info
        self.netprofiler.api.host_group_types.set(self.name, self.description,
                                                  self.favorite, self.config)

    def add_host_group(self, new_host_group):
        """ Add a new host group to groups dictionary.

        :param new_host_group: the new HostGroup to be added

        """
        if new_host_group.name in self.groups.keys():
            raise RvbdException('Host group: "{0}" already exists.'
                                .format(self.name))

        self.groups[new_host_group.name] = new_host_group

    def delete(self):
        """Delete this host group type and all groups."""
        if self.id is None:
            raise RvbdException('Type: "{0}" has not yet been saved to the '
                                'Netprofiler, so there is nothing to delete. '
                                'Call $host_group_type.save() first to save it.'
                                .format(self.name))
        self.netprofiler.api.host_group_types.delete(self.id)
        self.id = None

    @classmethod
    def _find_id(cls, netprofiler, name):
        # Get the ID of the host type specified by name
        host_types = netprofiler.api.host_group_types.get_all()
        target_type_id = None
        for host_type in host_types:
            if name == host_type['name']:
                target_type_id = host_type['id']
                break
        # If target_type_id is still -1, then we didn't find that host
        if target_type_id is None:
            raise RvbdException('{0} is not a valid type name '
                                'for this netprofiler'.format(name))
        return target_type_id


class HostGroup(object):
    # This is a convenience class to work with a single host
    # group definition.  We don't want to store the actual
    # host group definitions here because as much as possible
    # we need to preserve the order of *all* config items
    # across host group definitions because of precedence
    #
    # As such, all operations like add/remove/clear
    # operate on hostgrouptype.config

    def __init__(self, hostgrouptype, name):
        """New object representing a host group by name."""
        if not isinstance(name, basestring):
            raise RvbdException("This host group's name is not a string.")
        self.host_group_type = hostgrouptype
        self.name = name

    def add(self, cidrs, prepend=False, keep_together=True,
            replace=False):
        """Add a CIDR to this definition.

        :param str or list cidrs: CIDR or list of CIDRS to add to this
            host group

        :param bool prepend: if True, prepend instead of append

        :param bool keep_together: if True, place
            new entries near the other entries in this
            hostgroup.  If False, append/prepend to
            relative to the entire list.

        :param bool replace: if True, replace existing
            config entries for this host group with ``cidrs``

        """
        # prepend, keep_together define where a new entry will
        # show up in hostgrouptype.config
        #
        # config = [ {'name': 'Boston',  'cidr': '10.99.1/24'},
        #            {'name': 'Boston',  'cidr': '10.99.2/24'},
        #            {'name': 'SanFran', 'cidr': '10.99.3/24'},
        #            {'name': 'SanFran', 'cidr': '10.99.4/24'},
        #            {'name': 'NewYork', 'cidr': '10.99.5/24'},
        #            {'name': 'NewYork', 'cidr': '10.99.6/24'},
        #
        # sanfran=HostGroup(hostgrouptype, 'SanFran')
        #
        # The following shows the 4 variations of prepend/keep_together:
        #
        # sanfran.add('10.99.7/24', prepend=False, keep_together=True)
        #   - new entry between 10.99.4 and 10.99.5
        #
        # sanfran.add('10.99.7/24', prepend=True, keep_together=True)
        #   - new entry between 10.99.2 and 10.99.3
        #
        # sanfran.add('10.99.7/24', prepend=False, keep_together=False)
        #   - new entry at the back (after 10.99.6)
        #
        # sanfran.add('10.99.7/24', prepend=True, keep_together=False)
        #   - new entry at the front (before 10.99.1)
        #
        # If replace=True, the position will be chosen based on entries
        # before being deleted.  If not entries exist, it will be
        # as if keep_together=False (so front or back)

        if isinstance(cidrs, basestring):
            cidrs = [cidrs]

        if replace:
            self.clear()

        # Format the cidrs to be in the correct format for the config
        old_config = self.host_group_type.config
        new_config = []
        for cidr in cidrs:
            new_config.append({'cidr': cidr, 'name': self.name})

        # Add the new_config in the correct location
        if keep_together and len(old_config) > 0:
            index = [i for i, j in enumerate(old_config)
                     if j['name'] == self.name]
            if len(index) != 0:
                if prepend:
                    self.host_group_type.config[index[0]:index[0]] = new_config
                else:
                    self.host_group_type.config[index[-1]+1:index[-1]+1] = new_config
                return
        if prepend:
            self.host_group_type.config[0:0] = new_config
        else:
            self.host_group_type.config.extend(new_config)

    def remove(self, cidrs):
        """Remove a CIDR from this host group.

        :param str or list cidrs: CIDR or list of CIDRS to remove from
            this host group

        """
        if isinstance(cidrs, basestring):
            cidrs = [cidrs]
        self.host_group_type.config = filter(
            lambda a: a['cidr'] not in cidrs or a['name'] != self.name,
            self.host_group_type.config)

    def clear(self):
        """Clear all definitions for this host group."""
        self.host_group_type.config = filter(lambda a: a['name'] != self.name,
                                             self.host_group_type.config)

    def get(self):
        """Return a list of CIDRs assigned to this host group."""
        return [i['cidr'] for i in self.host_group_type.config
                if i['name'] == self.name]

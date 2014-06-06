# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

# Examples:
#
#   >>> byloc = HostGroupType.find_by_name(netprofiler, 'ByLocation')
#
#   >>> byloc.group['sanfran']
#   <HostGroup 'sanfran'>
#
#   >>> byloc.group['sanfran'].get()
#   ['10.99.1/24']
#
#   >>> byloc.group['sanfran'].add('10.99.2/24')
#   ['10.99.1/24', '10.99.2/24']
#
#   >>> byloc.save()
#

class HostGroupType(object):

    def __init__(self, netprofiler, id):
        # Host group id
        self.id = id

        # Properties filled in by load or by create
        self.name
        self.favorite
        self.description

        # Array of cidr/name config items
        self.config = []

        # Dictionary of HostGroup entries by name
        self.groups = {}

    @classmethod
    def find_by_name(cls, netprofiler, name):
        """Find and load a host group type by name."""
        pass

    @classmethod
    def create(cls, name, favorite=False, description=''):
        """Create a new hostgroup type.

        The new host group type will be created on the NetProfiler
        when save() is called.

        """

    def load(self):
        """Load settings and groups."""
        pass

    def save(self):
        """Save settings and groups.

        If this is a new host group type, it will be created.
        """
        pass

    def delete(self):
        """Delete this host group type and all groups."""
        pass


class HostGroup(object):

    # This is a convienence class to work with a single host
    # group definition.  We don't want to store the actual
    # host group defintions here because as much as possible
    # we need to preserve the order of *all* config items
    # across host group definitions because of precedence
    #
    # As such, all operations like add/remove/clear
    # operate on hostgrouptype.config

    def __init__(self, hostgrouptype, name):
        """New object represeting a host group by name."""
        pass

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
        pass

    def remove(self, cidrs):
        """Remove a CIDR from this host group.

        :param str or list cidrs: CIDR or list of CIDRS to remove from
            this host group

        """
        pass

    def clear(self):
        """Clear all definitions for this host group."""
        pass

    def get(self):
        """Return a list of CIDRs assigned to this host group."""
        pass

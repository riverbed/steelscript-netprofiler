# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.netprofiler.core import _constants


"""
This module contains classes to define and collect netprofiler data types
of Column, and Area.
"""


class Container(object):
    pass


class Column(object):
    """A column object represents a single data column in Profiler terms"""
    def __init__(self, cid, key, label, json, baseid=None, ephemeral=False):
        # Numeric column id.  This may be ephemeral -- meaning
        # its a really big number like 100000+.  For a given report
        # all columns in the report must have different ids.
        #
        # Non-ephemeral ids are static, like avg_bytes is always 33
        #
        # Ephemeral ids are dynamic and assigned for a specific
        # report only.  They are used in cases like top-N reporting
        # where there are multiple 'avg_bytes' columns, one for each
        # proto/port (for example).  In this case baseid refers to
        # the base columns type that tells you the general information
        # about the column, and the id will be what you use to request
        # data from the report.
        self.id = cid
        self.key = key
        self.label = label
        self.json = json
        self.iskey = json['category'] != 'data'
        self.baseid = (baseid or cid)
        self.ephemeral = ephemeral

    @classmethod
    def from_json(cls, json):
        ephemeral = json['id'] >= _constants.EPHEMERAL_COLID
        strid = json['strid']
        if strid.startswith('ID_'):
            key = strid.lower()[3:]
        else:
            # Current known use cases, this is a number
            # and is equal to str(json['id'])
            key = strid

        return Column(json['id'], key, json['name'],
                      json=json, ephemeral=ephemeral)

    def __eq__(self, other):
        return self.key == other

    def __cmp__(self, other):
        return cmp(self.key, other.key)

    def __hash__(self):
        return hash(tuple(self.json.values()))

    def __repr__(self):
        if self.baseid and self.baseid != self.id:
            msg = ('<steelscript.netprofiler.core._types.Column(id={0} '
                   'key={1} iskey={2} label={3} baseid={4})>')
            return msg.format(self.id, self.key, self.iskey, self.label,
                              self.baseid)
        else:
            msg = ('<steelscript.netprofiler.core._types.Column(id={0} '
                   'key={1} iskey={2} label={3})>')
            return msg.format(self.id, self.key, self.iskey, self.label)


class Area(object):
    def __init__(self, name, key):
        self.name = name
        self.key = key


class AreaContainer(object):
    """Wrapper class for Area objects
    """
    # TODO use actual Area objects in here
    def __init__(self, areas):
        """Initialize with list of key/value pairs
        """
        self._update(areas)

    def _update(self, areas):
        for k, v in areas:
            # TODO tests are looking at keys:values and values:keys
            # do we need bi-directional lookups?
            setattr(self, k, k)
            setattr(self, v, v)


class ColumnContainer(object):
    """Wrapper class for key and value Column classes
    Can be iterated against to get combined results.
    """
    def __init__(self, columns):
        self.key = Container()
        self.value = Container()
        self._map = dict()
        self._update(columns)

    def __getitem__(self, key):
        return self._map[key]

    def __iter__(self):
        """Iterates over keys and values to provide combined Column results.
        """
        for c in self.keys:
            yield c
        for c in self.values:
            yield c

    def __contains__(self, key_or_id):
        return key_or_id in self._map

    def _update(self, columns):
        """Take list of Column objects and apply their keys and ids as attributes.
        """
        for c in columns:
            self._map[c.key] = c
            self._map[c.id] = c
            if c.iskey:
                setattr(self.key, c.key, c)
            else:
                setattr(self.value, c.key, c)

    @property
    def keys(self):
        """Return the collection of 'key' Column objects.
        """
        try:
            return self.key.__dict__.values()
        except AttributeError:
            return None

    @property
    def values(self):
        """Return the collection of 'value' Column objects.
        """
        try:
            return self.value.__dict__.values()
        except AttributeError:
            return None

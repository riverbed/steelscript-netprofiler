# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


"""
This module contains classes to define and collect profiler data types
of Column, and Area.
"""
class Container(object):
    pass


class Column(object):
    def __init__(self, cid, key, label, json):
        self.id = cid
        self.key = key
        self.label = label
        self.json = json
        self.iskey = json['category'] != 'data'

    def __eq__(self, other):
        return self.key == other 

    def __cmp__(self, other):
        return cmp(self.key, other.key)

    def __hash__(self):
        return hash(tuple(self.json.values()))
        
    def __repr__(self):
        msg = '<rvbd.profiler._types.Column(id={0}, key={1}, iskey={2} label={3})>'
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


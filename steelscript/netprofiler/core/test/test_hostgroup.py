
from steelscript.netprofiler.core import NetProfiler
from steelscript.netprofiler.core.hostgroup import HostGroup, HostGroupType
from steelscript.common.service import UserAuth
from steelscript.common.exceptions import RvbdException

import unittest
import logging

try:
    from testconfig import config
except ImportError:
    if __name__ != '__main__':
        raise
    config = {}

# XXX we try to use unittest.SkipTest() in setUp() below but it
# isn't supported by python 2.6.  this simulates the same thing...
# another 2.6 hack
if 'profilerhost' not in config:
    __test__ = False

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)-5.5s] %(msg)s")


def create_profiler():
    """ Create NetProfiler instance given configuration data
    """
    if 'profilerhost' not in config:
        raise unittest.SkipTest('no netprofiler hostname provided')
    try:
        username = config['username']
    except KeyError:
        username = 'admin'
    try:
        password = config['password']
    except KeyError:
        password = 'admin'
    auth = UserAuth(username, password)
    return NetProfiler(config['profilerhost'], auth=auth)


class HostGroupTests(unittest.TestCase):
    def setUp(self):
        self.profiler = create_profiler()

    def test_find_by_name(self):
        """ Check that it finds ByLocation as a HostGroupType """
        host_group_type = HostGroupType.find_by_name(self.profiler, "ByLocation")
        self.assertEqual(host_group_type.name, "ByLocation")

    def test_create_save_and_delete(self):
        """ Check that when you create a new group type that it is added """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        host_group_type.save()
        host_copy = HostGroupType.find_by_name(self.profiler, "TestType")
        host_group_type.delete()
        self.assertEqual(host_group_type.id, host_copy.id)

    def test_group_keeptogether_and_append(self):
        """
        Check that you can add host groups and that it responds correctly
        When you append an element to the end with keep_together=True
        """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        # Create a bunch of new host groups for testing
        new_host_groups = []
        for i in range(10):
            new_host_groups.append(HostGroup(host_group_type, 'Test'+str(i)))
            new_host_groups[i].add("10.9{0}.11.0/24".format(i), keep_together=True, prepend=False)
            host_group_type.add_host_group(new_host_groups[i])
        # Add our special host group that will be what we focus on
        new_host_groups[9].add("10.10.21.0/24", keep_together=True, prepend=False)
        host_group_type.save()
        # If everything went well, the new host group will be the 2nd element
        self.assertEqual(host_group_type.groups['Test9'].get()[1], "10.10.21.0/24")
        host_group_type.delete()

    def test_replace(self):
        """
        Check that the replace parameter works when adding groups.
        """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        # Create a bunch of new host groups for testing
        new_host_groups = []
        for i in range(10):
            new_host_groups.append(HostGroup(host_group_type, 'Test'+str(i)))
            new_host_groups[i].add("10.9{0}.11.0/24".format(i),
                                   keep_together=True, prepend=False)
            host_group_type.add_host_group(new_host_groups[i])
        # Add our special host group that will be what we focus on
        new_host_groups[9].add("10.10.21.0/24", keep_together=True,
                               prepend=False, replace=True)
        host_group_type.save()
        # If everything went well, the new host group will be the 1st element
        self.assertEqual(host_group_type.groups['Test9'].get()[0], "10.10.21.0/24")
        self.assertEqual(len(host_group_type.groups['Test9'].get()), 1)
        host_group_type.delete()

    def test_remove_group(self):
        """
        Check that the remove method in HostGroup works properly by adding a few
        cidrs that have the same value, but are in different host groups, then
        removing one of those entries from one host group to make sure the other
        is not effected.
        """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        # Create a bunch of new host groups for testing
        new_host_groups = []
        for i in range(10):
            new_host_groups.append(HostGroup(host_group_type, 'Test'+str(i)))
            new_host_groups[i].add("10.9{0}.11.0/24".format(i),
                                   keep_together=True, prepend=False)
            host_group_type.add_host_group(new_host_groups[i])
        # Add our special host group that will be what we focus on
        new_host_groups[9].add("10.10.21.0/24", keep_together=True,
                               prepend=False)
        new_host_groups[8].add("10.10.21.0/24", keep_together=True,
                               prepend=False)
        new_host_groups[9].remove("10.10.21.0/24")

        host_group_type.save()
        # If everything went well, the new host group will be the 2nd element
        self.assertEqual(host_group_type.groups['Test9'].get()[0], "10.99.11.0/24")
        self.assertEqual(host_group_type.groups['Test8'].get()[1], "10.10.21.0/24")
        self.assertEqual(len(host_group_type.groups['Test9'].get()), 1)
        host_group_type.delete()

    def test_group_keeptogether_and_prepend(self):
        """
        Check that you can add host groups and that it responds correctly
        when you prepend an element first on the list that it works
        """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        # Create a bunch of new host groups for testing
        new_host_groups = []
        for i in range(10):
            new_host_groups.append(HostGroup(host_group_type, 'Test'+str(i)))
            new_host_groups[i].add("10.9{0}.11.0/24".format(i),
                                   keep_together=True, prepend=False)
            host_group_type.add_host_group(new_host_groups[i])
        # Add our special host group that will be what we focus on
        new_host_groups[0].add("10.10.21.0/24", keep_together=True, prepend=True)
        host_group_type.save()
        # If everything went well, the new host group will be the 2nd element
        self.assertEqual(host_group_type.groups['Test0'].get()[0], "10.10.21.0/24")
        host_group_type.delete()

    def test_abusive_input(self):
        """
        Check that after a series of weirdly placed loads, saves, and additions,
        the program handles everything correctly
        """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        self.assertRaises(RvbdException, host_group_type.add_host_group,
                          HostGroup("Hurtful", host_group_type))
        self.assertRaises(RvbdException, host_group_type.load)
        host_group_type.save()
        host_group_type.delete()
        self.assertRaises(RvbdException, host_group_type.delete)
        host_group_type.create(self.profiler, "AnotherTestType", False, "PODLE")
        self.assertRaises(RvbdException, host_group_type.load)
        host_group_type.add_host_group(HostGroup(host_group_type, "TestGroup"))
        host_group_type.groups['TestGroup'].get()
        host_group_type.config = host_group_type.groups['TestGroup'].get()

    def test_empty_get(self):
        """ Check that you get an empty array when you try to get an empty group
        """
        host_group_type = HostGroupType.create(self.profiler, "TestType")
        new_host_group = HostGroup(host_group_type, "EmptyGroup")
        self.assertEqual(new_host_group.get(), [])

if __name__ == '__main__':
    # for standalone use take one command-line argument: the netprofiler host
    import sys
    assert len(sys.argv) == 2

    config = {'profilerhost': sys.argv[1]}
    sys.argv = [sys.argv[0]]

    unittest.main()


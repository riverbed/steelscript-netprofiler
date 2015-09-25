#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import csv
import sys
import string
import optparse
from collections import defaultdict

from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.hostgroup import HostGroupType, HostGroup
from steelscript.commands.steel import prompt_yn
from steelscript.common.exceptions import RvbdException


# This script will take a file with subnets and SiteNames
# and create a HostGroupType on the target NetProfiler.
# If the HostGroupType already exists, it will be deleted,
# before creating a new one with the same name.
#
# See the EXAMPLE text below for the format of the input
# file.  Note that multiple SiteNames with different
# IP address spaces can be included.


EXAMPLE = """
subnet SiteName
10.143.58.64/26 CZ-Prague-HG
10.194.32.0/23 MX-SantaFe-HG
10.170.55.0/24 KR-Seoul-HG
10.234.9.0/24 ID-Surabaya-HG
10.143.58.63/23 CZ-Prague-HG
"""


class HostGroupImport(NetProfilerApp):

    def add_options(self, parser):
        super(HostGroupImport, self).add_options(parser)
        group = optparse.OptionGroup(parser, "HostGroup Options")
        group.add_option('--hostgroup', action='store',
                         help='Name of hostgroup to overwrite')
        group.add_option('-i', '--input-file', action='store',
                         help='File path to hostgroup file')
        parser.add_option_group(group)

    def validate_args(self):
        """Ensure all arguments are present."""
        super(HostGroupImport, self).validate_args()

        if not self.options.input_file:
            self.parser.error('Host group file is required, specify with '
                              '"-i" or "--input-file"')

        if not self.options.hostgroup:
            self.parser.error('Hostgroup name is required, specify with '
                              '"--hostgroup"')

    def validate(self, name):
        valid = set(string.letters + string.digits + '.-_')
        return all(c in valid for c in name)

    def import_file(self):
        """Process the input file and load into dict."""
        groups = defaultdict(list)

        with open(self.options.input_file, 'rb') as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)
            reader = csv.reader(f, dialect)
            header = reader.next()
            if header != ['subnet', 'SiteName']:
                print 'Invalid file format'
                print 'Ensure file has correct header.'
                print 'example file:'
                print EXAMPLE

            for i, row in enumerate(reader):
                cidr, group = row
                if not self.validate(group):
                    print 'Invalid group name on line %d: %s' % (i+2, group)
                    sys.exit()
                groups[group].append(cidr)

        return groups

    def update_hostgroups(self, groups):
        """Replace existing HostGroupType with contents of groups dict."""
        # First find any existing HostGroupType
        try:
            hgtype = HostGroupType.find_by_name(self.netprofiler,
                                                self.options.hostgroup)
            hgtype.config = []
            hgtype.groups = {}
            print ('Existing HostGroupType "%s" found.'
                   % self.options.hostgroup)
        except RvbdException:
            print 'No existing HostGroupType found, creating a new one.'

            hgtype = HostGroupType.create(self.netprofiler,
                                          self.options.hostgroup)

        # Add new values
        for group, cidrs in groups.iteritems():
            hg = HostGroup(hgtype, group)
            hg.add(cidrs)

        # Save to NetProfiler
        hgtype.save()
        print ('HostGroupType "%s" configuration saved.'
               % self.options.hostgroup)

    def main(self):
        """Confirm overwrite then update hostgroups."""

        confirm = ('The contents of hostgroup %s will be overwritten '
                   'by the file %s, are you sure?'
                   % (self.options.hostgroup, self.options.input_file))
        if not prompt_yn(confirm):
            print 'Okay, aborting.'
            sys.exit()

        groups = self.import_file()
        self.update_hostgroups(groups)
        print 'Successfully updated %s on %s' % (self.options.hostgroup,
                                                 self.netprofiler.host)


if __name__ == '__main__':
    HostGroupImport().run()

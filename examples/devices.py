#!/usr/bin/env python

# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.




from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.common.utils import Formatter

import optparse
from itertools import izip

import logging
logger = logging.getLogger(__name__)

class DeviceReport(NetProfilerApp):

    def add_options(self, parser):
        group = optparse.OptionGroup(parser, "Device List Options")
        group.add_option('-t', '--typeid', dest='typeid', default=None,
                         help='filter by type id integer')
        group.add_option('-c', '--cidr', dest='cidr', default=None,
                         help='filter by cidr subnets')
        group.add_option('-i', '--ipaddr', dest='ipaddr', default=None,
                         help='return details for specific ip address')
        group.add_option('--typelist', action='store_true', dest='typelist', default=False,
                         help='return type information')
        parser.add_option_group(group)
        logger.info('added option group')

    def validate_args(self):
        """ Check that ipaddr is mutually exclusive from typeid, cidr and typelist
        """
        logger.info('validating base options')
        super(DeviceReport, self).validate_args()

        logger.info('validating custom options')
        if sum([self.options.ipaddr is not None,
                (self.options.typeid is not None or self.options.cidr is not None),
                self.options.typelist]) > 1:
            self.optparse.error('ipaddr, (typeid/cidr), and typelist '
                                'are mutually exclusive, '
                                'choose from only one group.')

    def main(self):
        """ Setup query and run report with default column set
        """
        logger.info('running main')

        if self.options.ipaddr:
            self.data = self.netprofiler.api.devices.get_details(self.options.ipaddr)
        elif self.options.typelist:
            self.data = self.netprofiler.api.devices.get_types()
        else:
            self.data = self.netprofiler.api.devices.get_all(self.options.typeid,
                                                          self.options.cidr)

        #from IPython import embed; embed()
        self.print_columns()

    def print_columns(self, paginate=None):
        """ Print out data in a nice formatted table

        `paginate` option will insert a new header after that many
        rows have been printed.  Defaults to None (only single header
        output).
        """
        if not self.data:
            print "No data found."
            return

        if self.options.typelist:
            # two columns only
            headers = ['type_id', 'type']
            data = self.data
        elif self.options.ipaddr:
            # single dict
            headers = self.data.keys()
            data = [self.data.values()]
        else:
            # assume objects are uniform and take keys from first one
            headers = self.data[0].keys()
            data = [d.values() for d in self.data]

        Formatter.print_table(data, headers, paginate=30)


if __name__ == '__main__':
    DeviceReport().run()

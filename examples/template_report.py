#!/usr/bin/env python

# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core.report import MultiQueryReport
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter

import optparse


class TemplateReportApp(NetProfilerApp):

    def add_options(self, parser):
        super(TemplateReportApp, self).add_options(parser)
        group = optparse.OptionGroup(parser, "Report Options")
        group.add_option('--template-id', dest='template_id',
                         help='Required - template ID to run report against')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Download Options")
        group.add_option('--pathname', dest='pathname',
                         help='Required - full absolute pathname '
                              'for downloaded report')
        group.add_option('--format', dest='fmt', default='pdf',
                         help='Format of download: pdf (default) or csv')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Filter Options")
        group.add_option('--timefilter', dest='timefilter',
                         default='last 1 hour',
                         help='Time range to analyze (default "last 1 hour") '
                              'other valid formats: '
                              '"4/21/13 4:00 to 4/21/13 5:00" '
                              'or "16:00:00 to 21:00:04.546"')
        group.add_option('--trafficexpr', dest='trafficexpr', default=None,
                         help='Traffic Expression to apply (default None)')
        parser.add_option_group(group)

    def validate_args(self):
        """ Ensure columns are included
        """
        super(TemplateReportApp, self).validate_args()

        if not self.options.template_id:
            self.parser.error('Template ID is required.')

        if not self.options.pathname:
            self.parser.error('Full path name required for downloaded report')

        if self.options.fmt and self.options.fmt not in ('pdf', 'csv'):
            self.parser.error(
                'Only valid options for "--format" are "pdf" or "csv"'
            )

    def main(self):

        self.timefilter = TimeFilter.parse_range(self.options.timefilter)
        if self.options.trafficexpr:
            self.trafficexpr = TrafficFilter(self.options.trafficexpr)
        else:
            self.trafficexpr = None

        with MultiQueryReport(self.netprofiler) as report:
            report.run(template_id=int(self.options.template_id),
                       timefilter=self.timefilter,
                       trafficexpr=self.trafficexpr)
            print('Report Template {id} successfully run.'
                  .format(id=self.options.template_id))

            self.netprofiler.conn.download(
                '/api/profiler/1.6/reporting/reports/{id}/view.{fmt}'
                .format(id=report.id, fmt=self.options.fmt),
                path=self.options.pathname,
                overwrite=True
            )

            print('Completed Report {id} downloaded to {path}.'
                  .format(id=report.id,
                          path=self.options.pathname))


if __name__ == '__main__':
    TemplateReportApp().run()

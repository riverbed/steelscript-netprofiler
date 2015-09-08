# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf import settings

from steelscript.appfwk.apps.alerting.senders import ConsoleSender
from steelscript.appfwk.apps.alerting.datastructures import Results

import logging
logger = logging.getLogger(__name__)


class LocalConsoleSender(ConsoleSender):
    def send(self, alert):
        s = getattr(settings, 'FOO', 34)
        print "LocalConsoleSender: Works! %s - %s (%s)" % (alert.level,
                                                           alert.message,
                                                           s)


def simple_trigger(df, context, params):
    """Find any values in column that exceed a given value.

    Required params:
    `column`: specify column to evaluate
    `value`:  threshold value, rows which exceed this value will
        be returned from the trigger
    """
    return Results().add_result((df[params['column']] > params['value']).any(),
                                severity=5)


def local_spike(df, context, params):
    """Find conditions where local spikes occur.

    Can operate against timeseries or other data.  Optional params:

    `column`: specify column to calculate against, defaults to first non-time
        column.
    `std`:    number of standard deviations to consider as a spike,
        defaults to 2
    """
    column = params.get('column', None)
    if column is None:
        if 'time' in df:
            column = df.drop('time', axis=1).columns[0]
        else:
            column = df.columns[0]

    std = params.get('std', 2)

    # extract the column as a Series
    s = df[column]
    delta = s.std() * std

    # create a boolean index where the values exceed the delta threshold
    idx = abs(s - s.mean()) > delta

    # then use this to create a new dataframe
    results = df[idx]

    # as an example, dynamically determine severity based on size of results
    severity = len(results) * 10 if len(results) < 10 else 99

    return Results().add_results(results, severity=severity)

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from rvbd.common import timeutils

import time
import calendar
import datetime


class TimeFilter:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __repr__(self):
        msg = '<rvbd.profiler.filters.TimeFilter(start={0}, end={1}>'
        return msg.format(self.start, self.end)

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    @classmethod
    def parse_range(cls, s):
        """ Take a range string `s` and return a TimeFilter object
        """
        (start, end) = timeutils.parse_range(s)
        return cls(start, end)

    def compare_time(self, t, resolution=60):
        """ Return True if time `t` falls in between start and end times.

            `t` may be a unix timestamp (float or string) or a datetime.datetime
            object

            `resolution` is the number of seconds to use for rounding.  Since
            Profiler stores data in one-minute increments, typically this
            should allow reasonable comparisons to report outputs.  Passing
            zero (`0`) in here will enforce strict comparisons.
        """
        # try converting to datetime object
        try:
            t = timeutils.string_to_datetime(t)
        except TypeError:
            pass

        # move everything to uniform utc timezone
        # string to datetime already returns utc, but if this is a
        # datetime object, we are just being safe here
        t = timeutils.force_to_utc(t)
        start = timeutils.force_to_utc(self.start)
        end = timeutils.force_to_utc(self.end)

        # by default, this will be one minute delta
        delta = datetime.timedelta(0, resolution, 0)
        return (start <= t <= end or
                abs(start - t) < delta or
                abs(end - t) < delta)

    def profiler_minutes(self, astimestamp=False, aslocal=False):
        """ Provide best guess of whole minutes for current time range

            `astimestamp` determines whether to return results in Unix
            timestamp format or as datetime.datetime objects (defaults
            to datetime objects).

            `aslocal` set to True will apply local timezone to datetime
            objects (defaults to UTC).

            Profiler reports out in whole minute increments, and for time
            deltas less than one minute (60 seconds) it will use the rounded
            minute from the latest timestamp.  For time deltas over one
            minute, lowest and highest rounded minutes are used, along with
            all in between.
        """
        def round_to_minute(t):
            return t - datetime.timedelta(seconds=t.second,
                                          microseconds=t.microsecond)

        if aslocal:
            start = timeutils.ensure_timezone(self.start).astimezone(timeutils.tzlocal())
            end = timeutils.ensure_timezone(self.end).astimezone(timeutils.tzlocal())
            tstamp = time.mktime
        else:
            start = timeutils.ensure_timezone(self.start).astimezone(timeutils.tzutc())
            end = timeutils.ensure_timezone(self.end).astimezone(timeutils.tzutc())
            tstamp = calendar.timegm
        delta = end - start

        one_minute = datetime.timedelta(0, 60, 0)
        if delta <= one_minute:
            t = round_to_minute(end)
            if astimestamp:
                return [int(tstamp(t.timetuple()))]
            else:
                return [t]
        else:
            result = []
            t = round_to_minute(start)
            while t <= round_to_minute(end):
                if astimestamp:
                    result.append(int(tstamp(t.timetuple())))
                else:
                    result.append(t)
                t = t + one_minute
            return result


class TrafficFilter:
    def __init__(self, filter):
        self.filter = filter

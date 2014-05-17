# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.netprofiler.core.netprofiler import NetProfiler


def new_device_instance(*args, **kwargs):
    # Used by DeviceManager to create a NetProfiler instance
    return NetProfiler(*args, **kwargs)

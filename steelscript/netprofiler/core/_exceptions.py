# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.



'''
Created on Jul 20, 2012

@author: vincenzo.ampolo@riverbed.com
'''

class ProfilerException(Exception): pass

class ProfilerHTTPException(ProfilerException):
    def __init__(self, *args, **kwargs):
        ProfilerException.__init__(self, *args, **kwargs)
        
class InvalidGroupbyException(ProfilerException):
    def __init__(self, *args, **kwargs):
        ProfilerException.__init__(self, *args, **kwargs)
        
class InvalidColumnException(ProfilerException):
    def __init__(self, *args, **kwargs):
        super(InvalidColumnException, self).__init__(*args, **kwargs)

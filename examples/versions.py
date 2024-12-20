#!/usr/bin/env python
'''
' Riverbed Community SteelScript
'
' .py
' Encoding: UTF8
' End of Line Sequence: LF
'
' Copyright (c) 2024 Riverbed Technology, Inc.
'
' This software is licensed under the terms and conditions of the MIT License
' accompanying the software ("License").  This software is distributed "AS IS"
' as set forth in the License.


Usage example in Bash:

export RIVERBED_NETPROFILER_HOST=n31-prf
export RIVERBED_NETPROFILER_USERNAME=yourusername
export RIVERBED_NETPROFILER_PASSWORD=******

python versions.py

'''

## Step 1. Import steelscript libraries in Python

from steelscript.netprofiler.core import NetProfiler
from steelscript.common.service import UserAuth

import os

## Step 2. Configure and connect the service object for NetProfiler

host = os.getenv('RIVERBED_NETPROFILER_HOST')
username = os.getenv('RIVERBED_NETPROFILER_USERNAME')
password = os.getenv('RIVERBED_NETPROFILER_PASSWORD')

auth = UserAuth(username, password)
netprofiler_service = NetProfiler(host, auth=auth)

## Step 3. Check versions info

print(f"NetProfiler version: {netprofiler_service.version}")

print(f"Supported API versions: {netprofiler_service.supported_versions}")

print(f"Services API url: {netprofiler_service._services_api}")
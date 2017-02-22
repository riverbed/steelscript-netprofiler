# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import pkg_resources

from django.apps import AppConfig

from steelscript.appfwk.apps.plugins import Plugin as AppsPlugin


class NetProfilerPlugin(AppsPlugin):
    title = 'NetProfiler Datasource Plugin'
    description = 'A Portal datasource plugin with example report'
    version = pkg_resources.get_distribution('steelscript.netprofiler').version
    author = 'Riverbed Technology'

    enabled = True
    can_disable = True

    devices = ['devices']
    datasources = ['datasources']
    reports = ['reports']


class SteelScriptAppConfig(AppConfig):
    name = 'steelscript.netprofiler.appfwk'
    # label cannot have '.' in it
    label = 'steelscript_netprofiler'
    verbose_name = 'SteelScript NetProfiler'

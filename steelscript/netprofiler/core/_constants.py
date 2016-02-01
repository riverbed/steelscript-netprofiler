# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

# Version ID for cache file validation
# Increment this when schema for columns or groupby/relams get updated
CACHE_VERSION = 1.1

# When NetProfiler runs a report and generates "dynamic" or "ephemeral"
# columns, they are given an id greater than or equal to 200000
EPHEMERAL_COLID = 200000

realms = ['traffic_summary',
          'traffic_overall_time_series',
          'hosts_time_series',
          'traffic_flow_list',
          'identity_list',
          'msq'
          ]

centricities = ['hos', 'int']

# full list of groupbys from recent API query
# includes originally 'excluded' items commented out
groupbys = dict([
#                    ('alert_level', 'alt'),
#                    ('analytic', 'anl'),
#                    ('analytic_category', 'anc'),
                    ('application', 'app'),
                    ('application_port', 'apt'),
                    ('application_protoport_qos', 'apq'),
                    ('device', 'dev'),
#                    ('event', 'evt'),
#                    ('flow', 'flw'),
                    ('group_pair_protoport', 'gpr'),
                    ('host', 'hos'),
                    ('host_and_vtep_pair', 'vhp'),
                    ('host_group', 'gro'),
                    ('host_group_pair', 'gpp'),
                    ('host_pair', 'hop'),
                    ('host_pair_protoport', 'hpr'),
                    ('interface', 'ifc'),
#                    ('interface_group', 'ifg'),
                    ('interface_qos', 'ifq'),
                    ('ip_mac', 'ipm'),
                    ('ip_mac_pair', 'ipp'),
                    ('ip_mac_pair_protoport', 'ipr'),
#                    ('metric', 'mtc'),
                    ('peer', 'per'),
                    ('peer_group', 'pgp'),
                    ('peer_ip_mac', 'pip'),
#                    ('policy', 'pol'),
                    ('port', 'por'),
                    ('port_group', 'pgr'),
                    ('protocol', 'pro'),
                    ('segment', 'seg'),
#                    ('service', 'svc'),
#                    ('service_component', 'scm'),
#                    ('service_full_aggregation', 'saf'),
#                    ('service_location_aggregation', 'sal'),
                    ('service_location_metric_aggregation', 'slm'),
#                    ('service_location_summary', 'sll'),
#                    ('service_segment', 'ssg'),
#                    ('service_segment_aggregation', 'sas'),
                    ('time', 'tim'),
                    ('time_host_user', 'thu'),
#                    ('topology_summary', 'tpl'),
                    ('total', 'mzt'),
#                    ('vtep', 'vtp'),
                    ('vtep_pair', 'vpa'),
#                    ('vtep_peer', 'vpe'),
                    ('vxlan', 'vxl')
                ])

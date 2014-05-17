#!/usr/bin/env python

# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.



# Submitted by Joshau Chessman <jchessman@riverbed.com>

import pprint
import numpy
import re
import paramiko
import optparse

from scipy import stats

import matplotlib.pyplot as plt

from steelscript.netprofiler.core.app import NetProfilerApp
from steelscript.netprofiler.core import *
from steelscript.netprofiler.core.filters import TimeFilter, TrafficFilter

def findStartEnd(data):
    if extendZero == True:
        start = 0
    else:
        start = int(min(data)) - 1

    end = int(max(data)) + 1

    qty = ((end - start) / data.__len__() + 1)

    #x_series = range(start, end, qty)
    x_series = []
    x = 0
    while x < data.__len__():
        x_series.append([])
        x = x + 1


    return(x_series)

def genGraph(data, dataList, percentileVal):
    fig = plt.figure()

    # Clean up the list
    newData = []
    for y in data:
        newData.append(y[0])

    #dataListPercentile = []
    #dataListMedian = []
    #for y in dataList:
        #dataListPercentile.append(y[1])
        #dataListMedian.append(y[0])
        #print "Median {}".format(y[0])
        #print y[1]


    x_series = findStartEnd(newData)
    #x_series1 = findStartEnd(newDataList)

    percentileAvg = stats.scoreatpercentile(dataList[0], percentileVal)[0]
    median = stats.scoreatpercentile(dataList[0], 50)[0]
    individual = stats.scoreatpercentile(dataList[1], percentileVal)[0]

    # data is y series 1
    # dataList is y series 2

    plt.plot(x_series, newData, label="Raw Data")
    #plt.plot(x_series, dataList, label="Bucketed Data")

    plt.xlabel("Time")
    plt.xticks(rotation="vertical")
    plt.ylabel("Bytes")
    plt.title("Percentile Graph")

    #create legend
    plt.legend(loc="upper left")

    #save figure to png
    plt.savefig(graphFilename)

def generatePercentile(columns, theTimeFilter, trafficFilter, centricity, dataRes):
    print "Running timeseries report"
    report = TrafficOverallTimeSeriesReport(netprofiler)

    report.run( columns = columns,
                timefilter = theTimeFilter,
                trafficexpr = TrafficFilter(trafficFilter),
                centricity = centricity,
                resolution = dataRes
                )

    data = report.get_data()
    report.delete()

    print "Getting data"
    dataList = fixBucket(data, int(sumTime))

    if outputData == True and clean == False:
        print "Data points:"
        for x in dataList[1]:
            print x[0]

    if graph == True:
        genGraph(data, dataList, percentileVal)

    #print '{}% Average Bytes is {}'.format(percentileVal, stats.scoreatpercentile(data, percentileVal)[0])
    if clean == False: print '{}% Average Bytes is {}'.format(percentileVal, stats.scoreatpercentile(dataList, percentileVal)[0])
    if Max == True and clean == False: print 'Maximum Average Bytes is {}'.format(max(data)[0])
    if Min == True and clean == False: print 'Minimum Average Bytes is {}'.format(min(data)[0])
    if Median == True and clean == False: print 'Median Average Bytes is {}'.format(stats.scoreatpercentile(data, 50)[0])
    if clean == True: print '{} {}'.format(trafficFilter, stats.scoreatpercentile(dataList[0], percentileVal)[0])

def fixBucket(data, sumTime):
    # We need to average the data to the correct bucket
    y = 0
    z = []
    dataList = []
    for x in data:
        y = y + 1
        z.append(x[0])
        if y % sumTime == 0:
            # Generate the average
            dataList.append([[numpy.mean(z)], [stats.scoreatpercentile(data, percentileVal)[0]]])
            z = []
        elif y == z.__len__():
            dataList.append([[numpy.mean(z)], [stats.scoreatpercentile(data, percentileVal)[0]]])
            z=[]
    return dataList

def listIfaceGroups(host, sshUsername, sshPassword):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(host, username=sshUsername, password=sshPassword)
    stdin, stdout, stderr = ssh.exec_command("/usr/mazu/bin/mazu-interfacegroups -l")
    type(stdin)

    sshOutput = stdout.readlines()

    print "To specify a interface group on the command line you separate the hierarchies with /"
    print "For example: ByRegion/North_America"

    for x in sshOutput:
        print x.rstrip()

def listGroupTypes(host, sshUsername, sshPassword):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(host, username=sshUsername, password=sshPassword)
    stdin, stdout, stderr = ssh.exec_command("/usr/mazu/bin/mazu-hostgrouping -o listgrouptypes")
    type(stdin)

    sshOutput = stdout.readlines()

    print "To specify a group type and group use the format GroupType:GroupName"
    print "For example: -r 'hostgroup ByLocation:Cambridge'"
    print "If you use just the group type name the script will automatically try"
    print "and pull down all groups and report against each individually."

    y = 0
    for x in sshOutput:
        if y > 0:
            group = x.split("\t")

            stdin, stdout, stderr = ssh.exec_command("/usr/mazu/bin/mazu-hostgrouping -o listgroups --group-type-name " + group[1].strip("\n"))
            type(stdin)

            sshOutput2 = stdout.readlines()

            print 'Group type: {}'.format(group[1].strip("\n"))

            v = 0
            for z in sshOutput2:
                if v > 0:
                    groupName = z.split("\t")
                    print '    Group: {}'.format(groupName[1].strip())
                else:
                    v = v + 1
        else:
            y = y + 1


def dispTrafficExpressionHelp(host):
    print "Look at http://" + host + "/help/netprofiler/reports/traffic_reports/expressions/c_expressions.htm"

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

# Parse command line options -- run with '-h' to see additional standard options
app = NetProfilerApp()
parser = app.optparse

parser.add_option("-s", "--sumTime", help="Number of minutes data should be bucketed in (normally 5)", default=5)
parser.add_option("-e", "--percentile", help="What percentile to show (default is 95)", default=95)
parser.add_option("--trafficExpressionHelp", help="Traffic expression help", action="store_true", default=False)
#parser.add_option("-a", "--allIndexes", help="Show the percentile for every interface on the system", action='store_true')

group1 = optparse.OptionGroup(parser,'time frame')
group1.add_option("-t", "--timeFilter", help="Time Filter in the form of either 'last x {m|h|d|w}' or '10-30-2012 10:30am to 10-31-2012 10:02am'", default="last 5 m")
parser.add_option_group(group1)

group2 = optparse.OptionGroup(parser,'traffic filter')
group2.add_option("-r", "--trafficFilter", help="Traffic to filter on (such as 'host 10/8 or another traffic expression). You can specify just a host group type (for example ByLocation) Try --trafficExpressionHelp for details.')", default="host 10/8")
parser.add_option_group(group2)

group3 = optparse.OptionGroup(parser,'data resolution')
group3.add_option("-d", "--dataResolution", help="Data resolution to force (options include 1min, 15min, hour, 6hour, day, week). Default is 1 minute.", default="1min")
parser.add_option_group(group3)

group4 = optparse.OptionGroup(parser,'output')
group4.add_option("--median", help="Show the median from the set", action="store_true", default=False)
group4.add_option("--max", help="Show the maximum from the set", action="store_true", default=False)
group4.add_option("--min", help="Show the minimum from the set", action="store_true", default=False)
group4.add_option("--clean", help="Show only the name and value - overrides all other output options", action="store_true", default=False)
#group4.add_option("--detail", help="Show as much detail on the data as possible (includes bucket data)", action="store_true", default=False)
group4.add_option("-o", "--outputData", help="Display the data used to determine the percentile", action="store_true", default=False)
parser.add_option_group(group4)

group5 = optparse.OptionGroup(parser,'list groups')
group5.add_option("--listInterfaceGroups", help="List all available interface groups", action="store_true", default=False)
group5.add_option("--listHostGroupTypes", help="List all available host group types", action="store_true", default=False)
parser.add_option_group(group5)

group6 = optparse.OptionGroup(parser,'ssh options')
group6.add_option("--sshPassword", help="Password for SSH")
group6.add_option("--sshUsername", help="Username for SSH")
parser.add_option_group(group6)

group7 = optparse.OptionGroup(parser,'graph options')
group7.add_option("--graph", help="Display a graph of the data", action="store_true", default=False)
group7.add_option("--individual", help="Display the percentile graph at each bucket point", action="store_true", default=False)
group7.add_option("--overall", help="Display a line at the percentile point", action="store_true", default=False)
group7.add_option("--extendZero", help="Extend the graph to zero", action="store_true", default=False)
group7.add_option("--graphFilename", help="Filename to save the graph with", default='output.png')
parser.add_option_group(group7)

# Parse the options
app.parse_args()
app.start_logging()

#detail = app.options.detail
extendZero = app.options.extendZero
graph = app.options.graph
if graph == True:
    try:
        graphFilename = app.options.graphFilename
    except:
        print "You must specify a filename if you request a graph"
        exit(1)

individual = app.options.individual
overall = app.options.overall
clean = app.options.clean
Median = app.options.median
Max = app.options.max
Min = app.options.min
dataRes = app.options.dataResolution
trafficFilter = app.options.trafficFilter
timeFilter = app.options.timeFilter
#allIndexes = app.options.allIndexes
allIndexes = False
listInterfaceGroups = app.options.listInterfaceGroups
listHostGroupTypes = app.options.listHostGroupTypes
host = app.host
trafficExpressionHelp = app.options.trafficExpressionHelp
percentileVal = int(app.options.percentile)
outputData = app.options.outputData
sshPassword = app.options.sshPassword
sshUsername = app.options.sshUsername
sumTime = app.options.sumTime

if not is_int(percentileVal) or percentileVal < 1 or percentileVal > 100:
    print "Percentile MUST be an integer between 1 and 100"
    exit(1)

# Validate the time filter
theTimeFilter=TimeFilter.parse_range(timeFilter)

def checkSet(value, label):
    if value is None:
        print "'%s' must be passed for this command" % label
        exit(1)

# Process every index on the system
if listInterfaceGroups == True or listHostGroupTypes == True or trafficExpressionHelp:
    # List the interface or host groups
    if listHostGroupTypes == True:
        checkSet(sshUsername, "sshUsername")
        checkSet(sshPassword, "sshPassword")
        listGroupTypes(host, sshUsername, sshPassword)
        exit()
    elif listInterfaceGroups == True:
        checkSet(sshUsername, "sshUsername")
        checkSet(sshPassword, "sshPassword")
        listIfaceGroups(host, sshUsername, sshPassword)
        exit()
    elif trafficExpressionHelp == True:
        dispTrafficExpressionHelp(host)
        exit()

if clean == False: print 'Reporting on: {}'.format(timeFilter)
if clean == False: print 'Using the traffic filter: {}'.format(trafficFilter)
if clean == False: print 'Data resolution is: {}'.format(dataRes)
if clean == False: print 'Calculating data based on: {}th percentile'.format(percentileVal)
if clean == False: print 'Averaging based on buckets of {} minutes'.format(sumTime)
if clean == False and graph == True: print 'Creating a graph stored in {}'.format(graphFilename)

if allIndexes == True:
    # Create a NetProfiler object
    profiler = NetProfiler(host, auth=app.options.auth)
    print 'Reporting on All Interfaces'
    # Get a list of the possible interfaces
    report = TrafficSummaryReport(netprofiler)

    report.run(groupby = netprofiler.groupbys.interface,
               columns = [netprofiler.columns.key.interface,
                          netprofiler.columns.key.interface_dns],
               sort_col = netprofiler.columns.key.interface,
               timefilter = theTimeFilter,
                                  trafficexpr = TrafficFilter(trafficFilter)
               )

    # Retrieve the data
    data = report.get_data()
    report.delete()

    # Get the list of interfaces
    for x in data:
        # For each interface we need to get a traffic report
        intExpr = TrafficFilter("interface " + x[0])

        # Create a new report based on the list of interfaces we received
        report = TrafficOverallTimeSeriesReport(netprofiler)
        report.run( columns = [netprofiler.columns.value.avg_bytes],
                    timefilter = theTimeFilter,
                    trafficexpr = intExpr,
                    centricity = "int",
                    resolution = dataRes
                    )

        report.get_legend()
        dataY = report.get_data()
        report.delete()

        string = "Reporting on interface "

        interface = x[1].split("|")

        if interface[1].__len__() > 0:
            string = string + interface[1]
        else:
            string = string + interface[0]

        if interface[4].__len__() > 0:
            string = string + ":" + interface[4]
        else:
            string = string + ":" + interface[2]

        print '{}}% Average Bytes is {}'.format(percentileVal, stats.scorepercentileat(dataY[0], percentileVal))

        if outputData == True:
            for x in data:
                print x[0]

else:
# Regular queries. This is handled as follows:
#    If the traffic expression is of type "host" a simple query will be run
#    If the traffic expression is of type "hostgroup" a query will be run against all subgroups
#    If the traffic expression is of type "interfacegroup" will be run against the interfaces within that group
#    If the traffic expression is of type "device" or "interface" the query will be run against that specific device or interface
#    Other types and complex expressions are not currently supported

    # Create a NetProfiler object
    profiler = NetProfiler(app.host, auth=app.auth)
    expType = trafficFilter.split(" ")

    if expType[0] == "host":
        # This is a host type expression
        groupby = netprofiler.groupbys.host
        centricity = "hos"
    elif expType[0] == "hostgroup":
        # This is a host group type expression
        groupby = netprofiler.groupbys.group
        centricity = "hos"
        # We will need to run a report by group to see all the sub-groups IF there is no group specified
    elif expType[0] == "interfacegroup":
        # This is an interface group type expression
        groupby = netprofiler.groupbys.interface
        centricity = "int"
    elif expType[0] == "device" or expType[0] == "interface":
        # This is a device or interface expression
        groupby = netprofiler.groupbys.interface
        centricity = "int"

    columns = [netprofiler.columns.value.avg_bytes]

    if expType[0] == "hostgroup" and not re.match('.+:.+', expType[1]):
        # Only the group type is specified so we need to get the list of hostgroups by SSH'ing to the host
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if clean == False: print "Getting list of host groups for host group type {}".format(expType[1])
        ssh.connect(host, username=sshUsername, password=sshPassword)
        stdin, stdout, stderr = ssh.exec_command("/usr/mazu/bin/mazu-hostgrouping -o listgroups --group-type-name " + expType[1])
        type(stdin)

        ssh = stdout.readlines()
        y = 0
        for x in ssh:
            if y > 0:
                # Skip the first line
                sshOut = x.split('\t')
                # Now generate the percentile for each group
                newTrafficFilter = trafficFilter + ":" + sshOut[1]
                if clean == False: print "Running stats for '{}'".format(newTrafficFilter)
                generatePercentile(columns, theTimeFilter, newTrafficFilter, centricity, dataRes)
            y = y + 1
    else:
        generatePercentile(columns, theTimeFilter, trafficFilter, centricity, dataRes)

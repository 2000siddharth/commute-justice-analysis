from osgeo import ogr
import csv
import sys
import time
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets import Streets

censussrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10_centroids.shp"
ogr.UseExceptions()
odDictionary = {}

def AppendRecordToDict(row):
  items = odDictionary[row[1]]
  items.append({row[0]: row[2:]})
  odDictionary[row[1]] = items

# Build a dictionary of lists of dictionarys where the outer 
# dictionary key is the origin (2nd column) and the inner 
# dictionary key is the destination (1st column) and the remainder
# are all the other fields
def BuildOriginDestinationDictionary():
  odsrc = "/Users/cthomas/Development/Data/Census/ca_od_main_JT00_2014.csv"
  
  n = 0
  with open(odsrc, mode='r') as infile:
    reader = csv.reader(infile)
    for row in reader:
      n = n + 1
      if (n % 10000) == 0:
        print ("Dictionary has {} records, current record is {}".format(str(len(odDictionary)), row))
      if row[1] in odDictionary:
         AppendRecordToDict(row)
      else:
         odDictionary[row[1]] = [{row[0]: row[2:]}]

def PreProcessBlockCentroidStreetLines():
  
  pointlog = "/Users/cthomas/Development/Data/spatial/Network/streets/new_block_centroid_intersections_extend.csv"
  streetsegmentlog = "/Users/cthomas/Development/Data/spatial/Network/streets/street_segment_block_centroid_connectors_extend.csv"

  pointlogfile = open(pointlog, 'w')
  streetlogfile = open(streetsegmentlog, 'w')
  pointlogfile.write('Geometry\tGeoID\n')
  streetlogfile.write('Geometry\tGeoID\n')

  dictGeoIDs = {}

  census = ogr.Open(censussrc, 0)
  censuslayer = census.GetLayer()

  odb = OriginDestinationDB()

  streets = Streets()

  dictGeoIDs = odb.GetProcessedGeoIDExtend()

  dctDistances = {}

  n = 0
  logLevel = 0

  # Make this multi threaded - http://www.craigaddyman.com/python-queues-and-multi-threading/
  # I took a stabe at this with parallel_collect_commute_stats_block_level but ran into
  # some concurrency issues with the osgeo layer object - will revisit at some point
  for censusblock in censuslayer:
    n += 1

    if (n % 2000) == 0:
      print ("Processed {}".format(str(n)))

    homegeoid = censusblock.GetField("GeoID")
    homeGeometry = censusblock.GetGeometryRef()

    if homegeoid not in dictGeoIDs:
      print("Processing Home GEO {}".format(homegeoid))
      streets.FilterNearbyStreets(logLevel, homeGeometry)
      nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, homeGeometry)
      if nearest_point_on_street != None:
        nearest_point_on_street_extended = streets.ExtendLine(logLevel, homeGeometry, nearest_point_on_street, 0.0000005)
        if nearest_point_on_street_extended != None:
          dictGeoIDs[homegeoid] = 'POINT (' + str(nearest_point_on_street_extended.GetX()) + ' ' + str(nearest_point_on_street_extended.GetY()) + ')'
          pointlogfile.write('POINT (' + str(nearest_point_on_street_extended.GetX()) + ' ' + str(nearest_point_on_street_extended.GetY()) + ')\t\'' + homegeoid + '\'\n')
          streetlogfile.write('LINESTRING (' + str(homeGeometry.GetX()) + ' ' + str(homeGeometry.GetY()) + ',' +
               str(nearest_point_on_street_extended.GetX()) + ' ' + str(nearest_point_on_street_extended.GetY()) + ')\t\'' + homegeoid + '\'\n')
        else:
          print("---- We could properly extend the nearest street connector {}".format(homegeoid))
      else:
        print("---- We could not find a nearest street for Block {}".format(homegeoid))
    else:
      print("Already processed {}".format(homegeoid))

    if (n % 10) == 0:
      pointlogfile.flush()
      streetlogfile.flush()

  census = None
  pointlogfile.close()
  streetlogfile.close()

# Run this once only - should be a separate file
# BuildOriginDestinationDictionary()

PreProcessBlockCentroidStreetLines()

# ProcessBlockCommute()


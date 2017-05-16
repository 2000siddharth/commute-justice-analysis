from osgeo import ogr
import csv
import sys
import time
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets import Streets


# From http://gis.stackexchange.com/questions/7436/how-to-add-attribute-field-to-existing-shapefile-via-python-without-arcgis?rq=1

# censussrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10.shp"
# censussrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10_centroids.shp"
censussrc = "/Users/cthomas/Development/Data/spatial/Census/los_angeles_block_centroids.shp"

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


# Iterate over every census block on the area (Los Angeles for now)
# and grab the geoid which is the block code, then find the centroid
# with that ID, then iterate over each of the origin IDs and find the
# target IDs, calculate the distance traveled for each and store in dictionary
def ProcessBlockCommute():

  census = ogr.Open(censussrc, 0)
  censuslayer = census.GetLayer()

  odb = OriginDestinationDB()
  cbc = CensusBlockCentroids()
  streets = Streets()

  dctDistances = {}

  censuslayer.SetAttributeFilter ("COUNTYFP10='037'")
 
  n = 0
  for censusblock in censuslayer:
    n = n + 1
    homegeoid = censusblock.GetField("GEOID10")
    homeGeometry = censusblock.GetGeometryRef()

    destinations = odb.GetDestinations(homegeoid)

    for destination in destinations:

      print ("Workign on [{}]: for {}".format(homegeoid, destination))

      destGeoID = destination[0]
      destfeature = cbc.GetBlockCentroid(destGeoID)
      destGeometry = destfeature.GetGeometryRef()

      shortestroute = streets.GetShortestRoute(homeGeometry, destGeometry)
      # print ("Shortest route is {}".format(shortestroute))

    if n >= 10:
      break;

  census = None

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

  cbc = CensusBlockCentroids()

  streets = Streets()

  dictGeoIDs = odb.GetProcessedGeoIDExtend()

  dctDistances = {}

  # censuslayer.SetAttributeFilter ("COUNTYFP10='037' and (GEOID10='060372077101020' or GEOID10='060372085022002')")
  # censuslayer.SetAttributeFilter ("COUNTYFP10='037' and GEOID10='060371235201000'")
  censuslayer.SetAttributeFilter ("COUNTYFP10='037'")

  n = 0
  logLevel = 0

  # Make this multi threaded - http://www.craigaddyman.com/python-queues-and-multi-threading/
  # I took a stabe at this with parallel_collect_commute_stats_block_level but ran into
  # some concurrency issues with the osgeo layer object - will revisit at some point
  for censusblock in censuslayer:
    n = n + 1

    if (n % 2000) == 0:
      print ("Processed {}".format(str(n)))

    homegeoid = censusblock.GetField("GEOID10")
    homeGeometry = censusblock.GetGeometryRef()

    destinations = odb.GetDestinations(homegeoid)
    if homegeoid not in dictGeoIDs:
      # print("Processing Home GEO {}".format(homegeoid))
      streets.FilterNearbyStreets(logLevel, homeGeometry)
      nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, homeGeometry)
      nearest_point_on_street = streets.ExtendLine(homeGeometry, nearest_point_on_street, 0.0000005)
      if nearest_point_on_street != None:
        dictGeoIDs[homegeoid] = 'POINT (' + str(nearest_point_on_street.GetX()) + ' ' + str(nearest_point_on_street.GetY()) + ')'
        pointlogfile.write('POINT (' + str(nearest_point_on_street.GetX()) + ' ' + str(nearest_point_on_street.GetY()) + ')\t\'' + homegeoid + '\'\n')
        streetlogfile.write('LINESTRING (' + str(homeGeometry.GetX()) + ' ' + str(homeGeometry.GetY()) + ',' + 
             str(nearest_point_on_street.GetX()) + ' ' + str(nearest_point_on_street.GetY()) + ')\t\'' + homegeoid + '\'\n')
    else:
      print("Already processed {}".format(homegeoid))
    #for destination in destinations:

     # destGeoID = destination[0]

      #destfeature = cbc.GetBlockCentroid(destGeoID)
      #if destfeature.GetField("COUNTYFP10") == "037":

#        if destGeoID not in dictGeoIDs:
 #         destGeometry = destfeature.GetGeometryRef()
  #        streets.FilterNearbyStreets(logLevel, destGeometry)
   #       nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, destGeometry)
    #      print ("   For Home GOEID {}:: Dest GEOID {},  we found Nearest Pt [{}] on street {}".format(
     #       homegeoid, destGeoID, nearest_point_on_street, nearest_street.GetField("FULLNAME")))
      #    if nearest_point_on_street != None:
  #          dictGeoIDs[destGeoID] = nearest_point_on_street
   #         nearestStreetX = nearest_point_on_street.GetX()
    #        nearestStreetY = nearest_point_on_street.GetY()
     #       pointlogfile.write('POINT (' + str(nearestStreetX) + ' ' + str(nearestStreetY) + ')\t\'' + destGeoID + '\'\n')
      #      streetlogfile.write('LINESTRING (' + str(destGeometry.GetX()) + ' ' +  str(destGeometry.GetY()) + ',' +
       #         str(nearestStreetX) + ' ' + str(nearestStreetY) + ')\t\'' + destGeoID + '\'\n')
   #   else:
    #    print ("Destination outside of LA County: {} for {}".format(destfeature.GetField("COUNTYFP10"), homegeoid))

   # if (n >= 20):
   #   break

    if (n % 10) == 0:
      pointlogfile.flush()
      streetlogfile.flush()

  census = None
  pointlogfile.close()
  streetlogfile.close()
  
# BuildOriginDestinationDictionary()

# print ("The en
#  for our block is {}".format(odDictionary["060372760001009"]))

# ProcessBlockCommute()

PreProcessBlockCentroidStreetLines()

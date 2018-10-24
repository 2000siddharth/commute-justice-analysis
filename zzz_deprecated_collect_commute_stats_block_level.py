from osgeo import ogr
import csv
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets import Streets
import configparser, os

# From http://gis.stackexchange.com/questions/7436/how-to-add-attribute-field-to-existing-shapefile-via-python-without-arcgis?rq=1



odDictionary = {}

def AppendRecordToDict(row):
  items = odDictionary[row[1]]
  items.append({row[0]: row[2:]})
  odDictionary[row[1]] = items

# Build a dictionary of lists of dictionarys where the outer 
# dictionary key is the origin (2nd column) and the inner 
# dictionary key is the destination (1st column) and the remainder
# are all the other fields
def BuildOriginDestinationDictionary(config):
  odsrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Origin_Destination'] + '.csv'
  
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
def ProcessBlockCommute(config):

  censussrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'][''Census_Block10_Centroids'] + '.shp'
  census = ogr.Open(censussrc, 0)
  censuslayer = census.GetLayer()

  odb = OriginDestinationDB()
  cbc = CensusBlockCentroids()
  streets = Streets()

  dctDistances = {}
 
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

### OBE DO NOT USE THIS !!!!!!!!!!!!!!   Use _with_extend instead
#
# def PreProcessBlockCentroidStreetLines():
#
#   pointlog = "/Users/cthomas/Development/Data/spatial/Network/streets/new_block_centroid_intersections.csv"
#   streetsegmentlog = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Street_Segment_Block_Centroid_Connectors'] + '.csv'
#
#   pointlogfile = open(pointlog, 'a')
#   streetlogfile = open(streetsegmentlog, 'a')
#   pointlogfile.write('Geometry\tGeoID\n')
#   streetlogfile.write('Geometry\tGeoID\n')
#
#   dictGeoIDs = {}
#
#   census = ogr.Open(censussrc, 0)
#   censuslayer = census.GetLayer()
#
#   odb = OriginDestinationDB()
#
#   cbc = CensusBlockCentroids()
#
#   streets = Streets()
#
#   dictGeoIDs = odb.GetProcessedGeoID()
#
#   dctDistances = {}
#   n = 0
#   logLevel = 0
#
#   # Make this multi threaded - http://www.craigaddyman.com/python-queues-and-multi-threading/
#   # I took a stabe at this with parallel_collect_commute_stats_block_level but ran into
#   # some concurrency issues with the osgeo layer object - will revisit at some point
#   for censusblock in censuslayer:
#     n = n + 1
#     homegeoid = censusblock.GetField("GEOID10")
#     homeGeometry = censusblock.GetGeometryRef()
#
#     destinations = odb.GetDestinations(homegeoid)
#     if homegeoid not in dictGeoIDs:
#       print("Processing Home GEO {}".format(homegeoid))
#       streets.FilterNearbyStreets(logLevel, homeGeometry)
#       nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, homeGeometry)
#       if nearest_point_on_street != None:
#         dictGeoIDs[homegeoid] = 'POINT (' + str(nearest_point_on_street.GetX()) + ' ' + str(nearest_point_on_street.GetY()) + ')'
#         pointlogfile.write('POINT (' + str(nearest_point_on_street.GetX()) + ' ' + str(nearest_point_on_street.GetY()) + ')\t\'' + homegeoid + '\'\n')
#         streetlogfile.write('LINESTRING (' + str(homeGeometry.GetX()) + ' ' + str(homeGeometry.GetY()) + ',' +
#              str(nearest_point_on_street.GetX()) + ' ' + str(nearest_point_on_street.GetY()) + ')\t\'' + homegeoid + '\'\n')
#     else:
#       print("Already processed {}".format(homegeoid))
#     #for destination in destinations:
#
#      # destGeoID = destination[0]
#
#       #destfeature = cbc.GetBlockCentroid(destGeoID)
#       #if destfeature.GetField("COUNTYFP10") == "037":
#
# #        if destGeoID not in dictGeoIDs:
#  #         destGeometry = destfeature.GetGeometryRef()
#   #        streets.FilterNearbyStreets(logLevel, destGeometry)
#    #       nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, destGeometry)
#     #      print ("   For Home GOEID {}:: Dest GEOID {},  we found Nearest Pt [{}] on street {}".format(
#      #       homegeoid, destGeoID, nearest_point_on_street, nearest_street.GetField("FULLNAME")))
#       #    if nearest_point_on_street != None:
#   #          dictGeoIDs[destGeoID] = nearest_point_on_street
#    #         nearestStreetX = nearest_point_on_street.GetX()
#     #        nearestStreetY = nearest_point_on_street.GetY()
#      #       pointlogfile.write('POINT (' + str(nearestStreetX) + ' ' + str(nearestStreetY) + ')\t\'' + destGeoID + '\'\n')
#       #      streetlogfile.write('LINESTRING (' + str(destGeometry.GetX()) + ' ' +  str(destGeometry.GetY()) + ',' +
#        #         str(nearestStreetX) + ' ' + str(nearestStreetY) + ')\t\'' + destGeoID + '\'\n')
#    #   else:
#     #    print ("Destination outside of LA County: {} for {}".format(destfeature.GetField("COUNTYFP10"), homegeoid))
#
#    # if (n >= 20):
#    #   break
#
#     if (n % 10) == 0:
#       pointlogfile.flush()
#       streetlogfile.flush()
#
#   census = None
#   pointlogfile.close()
#   streetlogfile.close()
#
# # BuildOriginDestinationDictionary()
#
# # print ("The en
# #  for our block is {}".format(odDictionary["060372760001009"]))
#
# # ProcessBlockCommute()
#
# PreProcessBlockCentroidStreetLines()
#

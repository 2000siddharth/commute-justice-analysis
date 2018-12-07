from osgeo import ogr
import csv
import sys
import time
from census.origin_destination_db import OriginDestinationDB
import configparser, os
from network.streets import Streets

ogr.UseExceptions()

def CreateBlockCentroidToStreetConnectorSegments(config):

  block_centroid_to_street_segment = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Block_Centroid_Connectors'] + '.csv'
  block_centroid_to_street_segment_file = open(block_centroid_to_street_segment, 'w')
  block_centroid_to_street_segment_file.write('Geometry\tGeoID\n')

  censussrc = config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] + config['SPATIAL']['Census_Block10_Centroids'] + '.shp'
  census = ogr.Open(censussrc, 0)
  censuslayer = census.GetLayer()

  odb = OriginDestinationDB()

  streets = Streets()

  # The thought here was to store the geoID in the database to allow for interrupted operation
  # but it doesn't look like I ever followed up with that.
  dictGeoIDs = odb.GetProcessedGeoIDExtend()

  dctDistances = {}

  n = 0
  logLevel = 0

  print("About to start processing census layer {}".format(censussrc))
  # Make this multi threaded - http://www.craigaddyman.com/python-queues-and-multi-threading/
  # I took a stab at this with parallel_collect_commute_stats_block_level but ran into
  # some concurrency issues with the osgeo layer object - will revisit at some point
  for censusblock in censuslayer:
    n += 1

    if (n % 2000) == 0:
      print ("+++ Processed {}".format(str(n)))

    homegeoid = censusblock.GetField("GeoID")
    homeGeometry = censusblock.GetGeometryRef()

    if homegeoid not in dictGeoIDs:
      print("    Processing Home GEO {}".format(homegeoid))
      streets.FilterNearbyStreets(logLevel, homeGeometry)
      nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, homeGeometry)
      if nearest_point_on_street != None:
        nearest_point_on_street_extended = streets.ExtendLine(logLevel, homeGeometry, nearest_point_on_street, 0.0000005)
        if nearest_point_on_street_extended != None:
          dictGeoIDs[homegeoid] = 'POINT (' + str(nearest_point_on_street_extended.GetX()) + ' ' + str(nearest_point_on_street_extended.GetY()) + ')'
          block_centroid_to_street_segment_file.write('LINESTRING (' + str(homeGeometry.GetX()) + ' ' + str(homeGeometry.GetY()) + ',' +
               str(nearest_point_on_street_extended.GetX()) + ' ' + str(nearest_point_on_street_extended.GetY()) + ')\t\'' + homegeoid + '\'\n')
        else:
          print("---- We could properly extend the nearest street connector {}".format(homegeoid))
      else:
        print("---- We could not find a nearest street for Block {}".format(homegeoid))
    else:
      print("Already processed {}".format(homegeoid))

    if (n % 10) == 0:
     # block_centroid_intersection_pointfile.flush()
      block_centroid_to_street_segment_file.flush()

  census = None
  # block_centroid_intersection_pointfile.close()
  block_centroid_to_street_segment_file.close()

def main(argv):

  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  CreateBlockCentroidToStreetConnectorSegments(config)

if __name__ == '__main__':
    main(sys.argv[1:])



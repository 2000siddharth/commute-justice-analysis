from osgeo import ogr
import sys
from census.origin_destination_db import OriginDestinationDB
import configparser, os
from network.streets import Streets

ogr.UseExceptions()

def CreateBlockCentroidToStreetConnectorSegments(config):

  la_clipped_streets_osm_src = config['SPATIAL']['BASE_STREET_PATH'] + \
                               config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'] + '.shp'

  censussrc = config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] + config['SPATIAL']['Census_Block10_Centroids'] + '.shp'
  census = ogr.Open(censussrc, 0)
  censuslayer = census.GetLayer()

  odb = OriginDestinationDB()

  streets = Streets(la_clipped_streets_osm_src)

  # The thought here was to store the geoID in the database to allow for interrupted operation
  # but it doesn't look like I ever followed up with that.
  dictGeoIDs = odb.GetProcessedGeoIDsOSM()

  n = 0
  logLevel = 0

  print("About to start processing census layer {}".format(censussrc))
  # Make this multi threaded - http://www.craigaddyman.com/python-queues-and-multi-threading/
  # I took a stab at this with parallel_collect_commute_stats_block_level but ran into
  # some concurrency issues with the osgeo layer object - will revisit at some point
  censuslayer.SetAttributeFilter("GeoID='060377019023015'")
  for censusblock in censuslayer:
    n += 1

    # if (n == 100):
    #   break

    if (n % 2000) == 0:
      print ("+++ Processed {}".format(str(n)))

    homegeoid = censusblock.GetField("GeoID")
    homeGeometry = censusblock.GetGeometryRef()

    if homegeoid not in dictGeoIDs:
      streets.FilterNearbyStreets(logLevel, homeGeometry)
      nearest_point_on_street, nearest_street = streets.GetNearestStreet(logLevel, homeGeometry)
      if nearest_point_on_street != None and nearest_street != None:
        print("Processing Home GEO {} amd street {}".format(homegeoid, nearest_street.GetField("OSMID")))
        nearest_street_geometry = streets.ConvertMultilinestringtoLinestring(nearest_street.GetGeometryRef().Clone())
        remaining_length, lat_long_key = streets.GetLengthFromMidpointToEnd(nearest_street_geometry,
                                                                            nearest_point_on_street)
        utmHomeGeometry = streets.TransformShape(homeGeometry)
        distance_to_edge = streets.DistanceBetweenPoints(utmHomeGeometry, nearest_point_on_street)
        print("For home geoid {} we have key {} with a distance {}".format(homegeoid, lat_long_key, str(distance_to_edge)))
        # odb.SetNearestStreetInfo(homegeoid, lat_long_key, distance_to_edge,
        #                          nearest_street.GetField("OSMID"), remaining_length)
      else:
        print("      ---- We could not find a nearest street for Block {}".format(homegeoid))
    else:
     print("     Already processed {}".format(homegeoid))

  census = None

def main(argv):

  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  CreateBlockCentroidToStreetConnectorSegments(config)

if __name__ == '__main__':
    main(sys.argv[1:])



from osgeo import ogr
import sys
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets import Streets
import configparser, os

# Iterate over every census block on the area (Los Angeles for now)
# and grab the geoid which is the block code, then find the centroid
# with that ID, then iterate over each of the origin IDs and find the
# target IDs, calculate the distance traveled for each and store in dictionary
def ProcessBlockCommutes(config):

  la_censussrc = config['SPATIAL']['BASE_STREET_PATH'] + \
                 config['SPATIAL'][''Census_Block10_Centroids'] + '.shp'

  census = ogr.Open(la_censussrc, 0)
  censuslayer = census.GetLayer()

  census_centroids = ogr.Open(la_censussrc)
  census_centroids_layer = census_centroids.GetLayer()

  odb = OriginDestinationDB()
  cbc = CensusBlockCentroids()
  streets = Streets()

  streets.InitNetwork()

  dctDistances = {}

  censuslayer.SetAttributeFilter("is_dest = 1")
  source_feature = censuslayer.GetNextFeature()
  source_geometry = source_feature.GetGeometryRef()

  n = 0
  for censusblock in censuslayer:
    n = n + 1
    homegeoid = censusblock.GetField("GeoID")
    census_centroids_layer.SetAttributeFilter("GEOID ='{}'".format(homegeoid))
    homeGeometry = census_centroids_layer.GetGeometryRef()

    homeGeometryPoint = (homeGeometry.GetX(), homeGeometry.GetY())

    destinations = odb.GetDestinations(homegeoid)

    for destination in destinations:

      print ("Working on [{}]: for {}".format(homegeoid, destination))

      destGeoID = destination[0]
      destfeature = cbc.GetBlockCentroid(destGeoID)
      destGeometry = destfeature.GetGeometryRef()

      destGeometryPoint = (destGeometry.GetX(), destGeometry.GetY())

      streets.CalculateShortestRoute(homeGeometryPoint, destGeometryPoint)

    if n >= 10:
      break;

  census = None

# Iterate over every census block on the area (Los Angeles for now)
# and grab the geoid which is the block code, then find the centroid
# with that ID, then iterate over each of the origin IDs and find the
# target IDs, calculate the distance traveled for each and store in dictionary
def ProcessBlockCommutesRAND(config):

  print("Starting")

#  census = ogr.Open(censussrc, 0)
  la_censussrc = config['SPATIAL']['BASE_STREET_PATH'] + \
                 config['SPATIAL'][''Census_Block10_Centroids'] + '.shp'

  rand_census_blocks_src = config['SPATIAL']['BASE_STREET_PATH'] + \
                           config['SPATIAL']['RAND_Singlesource_Tabblock'] + '.shp'

  census = ogr.Open(rand_census_blocks_src, 0)
  censuslayer = census.GetLayer()

  census_centroids = ogr.Open(la_censussrc)
  census_centroids_layer = census_centroids.GetLayer()

  odb = OriginDestinationDB()
  cbc = CensusBlockCentroids()
  streets = Streets()

  streets.InitNetworkGraphSimple()

  print("Streets Inited")

  if 1 == 1:

    dctDistances = {}

    censuslayer.SetAttributeFilter("is_dest = 1")
    source_feature = censuslayer.GetNextFeature()
    work_geoid = source_feature.GetField("GeoID")
    census_centroids_layer.SetAttributeFilter("GEOID ='{}'".format(work_geoid))
    work_feature = census_centroids_layer.GetNextFeature()
    work_geometry = work_feature.GetGeometryRef()

    print("Working on work geometry with an X {} and Y {}".format(str(work_geometry.GetX()), str(work_geometry.GetY())))

    work_point = (work_geometry.GetX(), work_geometry.GetY())

    # work_point_id = streets.GetNodeID(work_point, "TNODE_")
    work_connector_street_id = streets.GetStreetIDFromNodeSimple(work_point, "FNODE_")

    print("Work Street ID: {}".format(work_connector_street_id))

    n = 0
    censuslayer.SetAttributeFilter("is_dest = 0")

    for censusblock in censuslayer:
      n += 1
      homegeoid = censusblock.GetField("GeoID")
      print ("Processing GEO ID {}".format(homegeoid))
      census_centroids_layer.SetAttributeFilter("GEOID ='{}'".format(homegeoid))
      home_feature = census_centroids_layer.GetNextFeature()
      home_geometry = home_feature.GetGeometryRef()
      home_point = (home_geometry.GetX(), home_geometry.GetY())

      # print("  We got the HOME geometry with an X {} and Y {}".format(str(home_geometry.GetX()), str(home_geometry.GetY())))

      route_id = streets.CalculateShortestRoute(home_point, work_connector_street_id)
      if (route_id != None):
        route_length = streets.MergeShortestRoute(route_id)
        odb.SetBlockCommute (homegeoid, work_geoid, route_length)
      if (n % 100 == 0):
        print("=== We've processed {} home origins ".format(str(n)))

    census = None


def main(argv):

  print("starting in main")
  ()
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  ProcessBlockCommutesRAND(config)

if __name__ == '__main__':
    main(sys.argv[1:])

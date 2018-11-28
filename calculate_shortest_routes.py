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
                 config['SPATIAL']['Census_Block10_Centroids'] + '.shp'

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

def main(argv):

  print("starting in main")
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  ProcessBlockCommutes(config)

if __name__ == '__main__':
    main(sys.argv[1:])

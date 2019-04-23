import configparser, os, sys
from osgeo import ogr
from census.origin_destination_db import OriginDestinationDB

def IsHomeCommuteBlock(odb, block_geoid):

  destinations = odb.GetDestinations(block_geoid)
  return (len(destinations) > 0)

def ProcessAllCentroids(config):

  odb = OriginDestinationDB()
  centroids_data = ogr.Open(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp', 0)
  centroids_layer = centroids_data.GetLayer()

  for feature in centroids_layer:
    h_geoid = feature.GetField("GeoID")
    geometry = feature.GetGeometryRef()
    easting = geometry.GetX()
    northing = geometry.GetY()
    is_commute_block = IsHomeCommuteBlock(odb, h_geoid)

    odb.InsertCensusBlock(h_geoid, easting, northing, is_commute_block)


def main(argv):

  print("starting in main")
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  ProcessAllCentroids(config)

if __name__ == '__main__':
    main(sys.argv[1:])

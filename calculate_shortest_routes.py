from osgeo import ogr
import csv
import sys
import time
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets import Streets

censussrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10_centroids.shp"
ogr.UseExceptions()

# Iterate over every census block on the area (Los Angeles for now)
# and grab the geoid which is the block code, then find the centroid
# with that ID, then iterate over each of the origin IDs and find the
# target IDs, calculate the distance traveled for each and store in dictionary
def ProcessBlockCommutes():

  census = ogr.Open(censussrc, 0)
  censuslayer = census.GetLayer()

  odb = OriginDestinationDB()
  cbc = CensusBlockCentroids()
  streets = Streets()

  dctDistances = {}

  n = 0
  for censusblock in censuslayer:
    n = n + 1
    homegeoid = censusblock.GetField("GeoID")
    homeGeometry = censusblock.GetGeometryRef()

    destinations = odb.GetDestinations(homegeoid)

    for destination in destinations:

      print ("Working on [{}]: for {}".format(homegeoid, destination))

      destGeoID = destination[0]
      destfeature = cbc.GetBlockCentroid(destGeoID)
      destGeometry = destfeature.GetGeometryRef()

      shortestroute = streets.GetShortestRoute(homeGeometry, destGeometry)
      # print ("Shortest route is {}".format(shortestroute))

    if n >= 10:
      break;

  census = None

  def main(argv):

    ProcessBlockCommutes()

  if __name__ == "__main__":
      main(sys.argv[1:])
from osgeo import ogr
import csv
import sys
import time
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets_parallel import Streets
import multiprocessing

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
  
  pointlog = "/Users/cthomas/Development/Data/spatial/Network/streets/parallel_block_centroid_intersections.csv"
  streetsegmentlog = "/Users/cthomas/Development/Data/spatial/Network/streets/parallel_street_segment_block_centroid_connectors.csv"

  pointlogfile = open(pointlog, 'w')
  streetlogfile = open(streetsegmentlog, 'w')
  pointlogfile.write('Geometry\tGeoID\n')
  streetlogfile.write('Geometry\tGeoID\n')

  dictGeoIDs = {}

  odb = OriginDestinationDB()

  cbc = CensusBlockCentroids()

  n = 0
  logLevel = 0

  # Make this multi threaded - http://www.craigaddyman.com/python-queues-and-multi-threading/
  # https://www.tutorialspoint.com/python/python_multithreading.htm
  # for each geoID in census blocks (use database h_geocode list, not census block shape map)
  #   geometry = GetGeometryByGeoID(geoID)
  #    q.put(census block geometry)
  # def process_node ():
  #   while not q.empty()
  #     geometry = q.get()
  #     streets.GetNearestStreet(logLevel, geometry)
  #     --- how do we add to a sync'd dictionary
  #     log the stuff
  #     now do the same for all work nodes
  #       -- dictionary check
  #       log the stuff
  #     q.task_done()
  # Now we create the threads
  # for i in range(10):  
  #   tl = Thread(target = process_node)
  #   tl.start()
  # q.join()

  home_geoids = multiprocessing.Queue
  manager = multiprocessing.Manager()
  odDictionary = manager.dict()

  num_processors = multiprocessing.cpu_count() * 2
  street_processors = [ Streets (logLevel, home_geoids, pointlogfile, streetlogfile, odDictionary, odb, cbc)
                        for i in xrange(num_processors)]

  for sp in street_processors:
    sp.start()

  num_geoids = 0

  for censusblock in odb.GetOriginsInCounty(6037):
    home_geoids.put(censusblock)
    num_geoids += 1

  for i in xrange(num_processors):
    home_geoids.put(None)

  pointlogfile.close()
  streetlogfile.close()

# ProcessBlockCommute()

PreProcessBlockCentroidStreetLines()


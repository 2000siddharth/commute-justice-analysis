from osgeo import ogr
import csv
import sys
import time
import random
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

class QueueManager(multiprocessing.Process):

    def __init__(self, odb, geoid_queue, pointlogfile, streetlogfile, num_processors):
    # for censusblock in odb.GetOriginsInCounty(6037):
        multiprocessing.Process.__init__(self)
        self.odb = odb
        self.geoid_queue = geoid_queue
        self.pointlogfile = pointlogfile
        self.streetlogfile = streetlogfile
        self.num_processors = num_processors
        self.process_count = 0

    def run(self):
        for censusblock in self.odb.GetOriginsInZipcode(90045):
          if not self.geoid_queue.full():
            print("Putting census block {}".format(censusblock[0]))
            self.geoid_queue.put(censusblock[0])
          else:
            time.sleep(random.random())

          self.process_count += 1

          if (self.process_count % 10) == 0:
              self.pointlogfile.flush()
              self.streetlogfile.flush()

        print ("DONE populating queue")
        for i in range(self.num_processors):
            self.geoid_queue.put(None)

def PreProcessBlockCentroidStreetLines():
  
  pointlog = "/Users/cthomas/Development/Data/spatial/Network/streets/parallel_block_centroid_intersections.csv"
  streetsegmentlog = "/Users/cthomas/Development/Data/spatial/Network/streets/parallel_street_segment_block_centroid_connectors.csv"

  pointlogfile = open(pointlog, 'w')
  streetlogfile = open(streetsegmentlog, 'w')
  pointlogfile.write('Geometry\tGeoID\n')
  streetlogfile.write('Geometry\tGeoID\n')

  odb = OriginDestinationDB()
  cbc = CensusBlockCentroids()

  logLevel = 0

  # Make this multiprocesed - http://www.craigaddyman.com/python-queues-and-multi-threading/
  # https://www.tutorialspoint.com/python/python_multithreading.htm

  num_geoids = 0
  home_geoids = multiprocessing.Queue()
  manager = multiprocessing.Manager()
  dictGeoIDs = manager.dict()

  num_processors = int(multiprocessing.cpu_count() / 2)
  print ("Beginning with {} processors".format(num_processors))

  street_processors = [ Streets (logLevel, home_geoids, pointlogfile, streetlogfile, dictGeoIDs, odb, cbc)
                        for i in range(num_processors)]

  qm = QueueManager(odb, home_geoids, pointlogfile, streetlogfile, num_processors)
  qm.start()

  time.sleep(2)

  for sp in street_processors:
    sp.start()

  for sp in street_processors:
      print("We have Process {} which is alive {}".format(sp, sp.is_alive()))

  #  for censusblock in odb.GetOriginsInCounty(6037):
#    home_geoids.put(censusblock[0])
#    num_geoids += 1
#    if num_geoids >= 20000:
#       break
#    if num_geoids % 1000 == 0:
#      print ("We've put {} censusblocks using {}".format(num_geoids, censusblock[0]))
#      for sp in street_processors:
#        print("We have Process {}".format(sp.is_alive()))

  for sp in street_processors:
    sp.join()

  pointlogfile.close()
  streetlogfile.close()

# ProcessBlockCommute()

if __name__ == '__main__':
  PreProcessBlockCentroidStreetLines()


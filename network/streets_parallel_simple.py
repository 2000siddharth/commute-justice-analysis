import time
from math import sqrt
from sys import maxsize
from itertools import tee
import multiprocessing
from multiprocessing.managers import SyncManager
from collections import deque

SyncManager.register('deque', deque)

class Streets(multiprocessing.Process):
  def __init__(self, logLevel, geoid_queue, pointlogfile, streetlogfile, odDictionary, odb, cbc):

    multiprocessing.Process.__init__(self)

    print("INITING {}".format(self.name))

    self.geoid_queue = geoid_queue
    self.pointlogfile = pointlogfile
    self.streetlogfile = streetlogfile
    self.dictGeoIDs = odDictionary
    self.odb = odb
    self.cbc = cbc
    self.process_count = 0

    print("DONE INITING {} and is alive: {}".format(self.name, self.is_alive()))

  def run(self):

    print ("Starting run in {}".format(self.name))
    while True:

      if not self.geoid_queue.empty():

        homegeoid = self.geoid_queue.get()

        if homegeoid is None:
          print ("Exiting {}".format(self.name))
          break

        print ("Procesing home id {} and we're empty {}".format(homegeoid, self.geoid_queue.empty()))

        self.process_count += 1
        if homegeoid not in self.dictGeoIDs:
          print("Processing Home GEO {}".format(homegeoid))
          self.dictGeoIDs[homegeoid] = homegeoid

    return
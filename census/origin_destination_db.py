import sqlite3
from .census_db import *

class OriginDestinationDB(CensusDB):

  # some constants about the database table
  tbl = 'origindestination'

  def GetOriginsInCounty(self, ctycode):
    destinationSQL = "SELECT h_geocode from origindestination od join xwalk x on od.h_geocode = x.block2010 where x.cty=?"
    result, destinations = self.select_many(destinationSQL, ctycode)
    return destinations

  def GetDestinations(self, origingeoid):
    
    destinationSQL = "SELECT * FROM origindestination WHERE h_geocode=?"
    result, destinations = self.select_many(destinationSQL, [origingeoid])
    return destinations

  def Get UniqueOrigins(self):
    destinationSQL = "SELECT distinct h_geocode FROM origindestination"
    result, destinations = self.select_many(destinationSQL, [origingeoid])
    return destinations


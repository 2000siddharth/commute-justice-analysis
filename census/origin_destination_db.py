import sqlite3
from .census_db import *

class OriginDestinationDB(CensusDB):

  # some constants about the database table
  tbl = 'origindestination'

  def GetDestinations(self, origingeoid):
    
    destinationSQL = "SELECT * FROM origindestination WHERE h_geocode=?"
    result, destinations = self.select_many(destinationSQL, [origingeoid])
    return destinations

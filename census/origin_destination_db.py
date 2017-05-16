import sqlite3
from .census_db import *

class OriginDestinationDB(CensusDB):

  # some constants about the database table
  tbl = 'origindestination'

  def GetOriginsInCounty(self, ctycode):
    destinationSQL = "SELECT distinct od.h_geocode FROM origindestination od join xwalk x on od.h_geocode = x.block2010 WHERE x.cty=?"
    result, destinations = self.select_many(destinationSQL, ctycode)
    return destinations

  def GetOriginsInZipcode(self, zctacode):
    destinationSQL = "SELECT distinct od.h_geocode FROM origindestination od join xwalk x on od.h_geocode = x.block2010 WHERE x.zcta=?"
    result, destinations = self.select_many(destinationSQL, zctacode)
    return destinations

  def GetDestinations(self, origingeoid):
    
    destinationSQL = "SELECT * FROM origindestination WHERE h_geocode=?"
    result, destinations = self.select_many(destinationSQL, [origingeoid])
    return destinations

  def GetProcessedGeoID(self):
    geoidsSQL = "SELECT geoid, geometry FROM block_centroid_intersection"
    result, geoids = self.select_many(geoidsSQL)
    geoidDict = {}
    for geoidsgeometry in geoids:
      geoidDict[geoidsgeometry[0]] = geoidsgeometry[1]
    return geoidDict

  def GetProcessedGeoIDExtend(self):
    geoidsSQL = "SELECT geoid, geometry FROM block_centroid_intersection_extend"
    result, geoids = self.select_many(geoidsSQL)
    geoidDict = {}
    for geoidsgeometry in geoids:
      geoidDict[geoidsgeometry[0]] = geoidsgeometry[1]
    return geoidDict


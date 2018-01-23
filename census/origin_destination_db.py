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

  def GetDestinationGeoIds(self, origingeoid):

    destinationSQL = "SELECT w_geocode FROM origindestination WHERE h_geocode=?"
    result, destinations = self.select_many(destinationSQL, origingeoid)
    return destinations

  def GetOriginGeoIds(self, destinationgeoid):

    destinationSQL = "SELECT h_geocode FROM origindestination WHERE w_geocode=?"
    result, origins = self.select_many(destinationSQL, destinationgeoid)
    return origins

  # Return the full data for each OD record for the destination (w_geocode)
  # specified in the request.  Values include the h_geocode and the
  # suite of 9 census characterstic bins
  def GetOriginFullData(self, destinationgeoid):

    destinationSQL = "SELECT h_geocode, s000, sa01, sa02, sa03, se01, se02, se03, si01, si02, si03" \
                     " FROM origindestination WHERE w_geocode=?"
    result, origins = self.select_many(destinationSQL, destinationgeoid)
    return origins

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

  def SetBlockCommute (self, homegeoid, workgeoid, route_length):
    setSQL = "UPDATE origindestination SET o_d_commute = ? WHERE h_geocode = ? and w_geocode = ?"
    # print ("about to execute SQL {} with homegeoid {} and workgeoid {} and length of {}".format(setSQL, homegeoid, workgeoid, route_length))
    self.exec(setSQL, (route_length, homegeoid, workgeoid))

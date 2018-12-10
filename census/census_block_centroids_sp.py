from osgeo import ogr, osr
import configparser, os, sys

class CensusBlockCentroids:

  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  SRID = 32711   # UTM zone 11S, WGS 84
  blocksrc = config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] + config['SPATIAL']['Census_Block10_Centroids'] + '.shp'

  blocknetwork = ogr.Open(blocksrc)
  blocklayer  = blocknetwork.GetLayer(0)

  sourceSpatialRef = blocklayer.GetSpatialRef()
  targetSpatialRef = osr.SpatialReference()
  targetSpatialRef.ImportFromEPSG(SRID)

  transform = osr.CoordinateTransformation(sourceSpatialRef, targetSpatialRef)

  # Return the node that is the census block centroid
  def GetBlockCentroid(self, blockcode):

    self.blocklayer.SetAttributeFilter("GEOID10 = '{}'".format(blockcode))
    blockCentroid = next(self.blocklayer)

    return blockCentroid

  def GetBlockGeoIDs(self):
    """Return a list of all block centroids in the area of interest"""
    geoids = []
    for feature in self.blocklayer:
      geoids.append(feature.GetField("GeoId"))

    return geoids
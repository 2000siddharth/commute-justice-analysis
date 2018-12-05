from osgeo import ogr, osr

class CensusBlockCentroids:

#  OGRSpatialReference oSRS
#  oSRS.SetWellKnownGeogCS( "EPSG:4269" )

  SRID = 32711   # UTM zone 11S, WGS 84
  blocksrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Census_Block10_Centroids'] + '.shp'

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


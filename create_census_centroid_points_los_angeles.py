from shapely.geometry import base, point, shape
from osgeo import ogr
from osgeo import osr
import fiona
import logging, sys

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Source file is all of california
block_source = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10.shp"
# Target will only include LA county
block_centroid_target = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10_centroids.shp"

driver = ogr.GetDriverByName("ESRI Shapefile")
data_source = driver.CreateDataSource(block_centroid_target)

# create the spatial reference, WGS84
srs = osr.SpatialReference()
srs.ImportFromEPSG(4326)

# create the layer
layer = data_source.CreateLayer("block_centroids", srs, ogr.wkbPoint)
field_name = ogr.FieldDefn("GeoID", ogr.OFTString)
field_name.SetWidth(16)
layer.CreateField(field_name)

with fiona.open(block_source, 'r') as source:

    for feat in source:

        try:
            censusblock = shape(feat['geometry'])
            block_centroid =  censusblock.centroid
            geom_id = feat['properties']['GEOID10']
            county_id = feat['properties']['COUNTYFP10']
            aland10 = feat['properties']['ALAND10']

            if (county_id == '037' and aland10 != 0):
                feature = ogr.Feature(layer.GetLayerDefn())
                # Set the attributes using the values from the delimited text file
                feature.SetField("GeoID", geom_id)

                # Create the point from the Well Known Txt
                centroid = ogr.CreateGeometryFromWkt(block_centroid.wkt)
                feature.SetGeometry(centroid)
                # Create the feature in the layer (shapefile)
                layer.CreateFeature(feature)
                # Dereference the feature
                feature = None

        except (Exception):
            logging.exception("Error cleaning feature %s:", feat['id'])
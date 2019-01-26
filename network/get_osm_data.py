import configparser, os, sys
from osgeo import ogr, osr
import decimal
import osmnx as ox
from shapely.geometry import mapping, shape
import fiona

def copy_feature_attribute_values(inFeature, outLayerDefn, outFeature):
  for i in range(0, outLayerDefn.GetFieldCount()):
    fieldName = outLayerDefn.GetFieldDefn(i).GetNameRef()
    field = inFeature.GetField(i)
    outFeature.SetField(fieldName, field)

def frange(start, stop, step):
  i = start
  while i <= stop:
    yield i
    i += step

def import_and_prep_data(config):

  driver = ogr.GetDriverByName('ESRI Shapefile')

  # Grab street centerline from OSM and then we'll clip them at the ~20 mile LA County buffer
  # Tried of all of California but Docker kept killing the process - could have set oom-kill-false
  # But after downloading 200 MB of data, ran into 8 GB memory ceiling - moved to graph_from_bbox

  east = -117.4
  west = -119.4
  south = 33.4
  north = 35.4

  ox.config(use_cache=True, log_console=True)

  greater_la_streets_box = ox.graph_from_bbox(north, south, east, west,
                                network_type='drive', simplify=True,
                                timeout=3600,
                                infrastructure='way["highway"~"motorway|trunk|primary|secondary|' \
                                'residential|motorway_link|trunk_link|primary_link"]')

  print ("   Saving to {}".format(config['SPATIAL']['CA_Street_Centerlines_OSM']))

  ox.save_graph_shapefile(greater_la_streets_box, filename=config['SPATIAL']['CA_Street_Centerlines_OSM'] + longlatkey,
                     folder=config['SPATIAL']['BASE_STREET_PATH'])

  # Now clip the OSM data and census blocks with the buffered LA Country polygon.
  la_clip_path = config['DEFAULT']['BASE_PATH_SPATIAL'] + config['SPATIAL']['LA_County_Buffered'] + '.shp'
  la_clip_path_src = ogr.Open(la_clip_path, 0)
  la_clip_layer = la_clip_path_src.GetLayer(0)
  spatial_ref = la_clip_layer.GetSpatialRef()

  print("About to clip Street Centerlines to buffered LA County area")

  california_streets = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Street_Centerlines_OSM'] + '.shp'
  california_streets_src = ogr.Open(california_streets, 0)
  california_streets_layer = california_streets_src.GetLayer(0)

  la_clipped_streets_src = driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                                                   config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'] + '.shp')
  la_clipped_streets_layer = la_clipped_streets_src.CreateLayer(config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'],
                                                                spatial_ref, ogr.wkbLineString)

  california_streets_layer.Clip(la_clip_layer, la_clipped_streets_layer)

  # print("About to clip Block Centroids to buffered LA County area")
  #
  # block_centroids = config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] + config['SPATIAL'][
  #   'Census_Block10_Centroids_Near_LA'] + '.shp'
  # block_centroids_src = ogr.Open(block_centroids, 0)
  # block_centroids_layer = block_centroids_src.GetLayer(0)
  #
  # block_centroids_clipped_src = driver.CreateDataSource(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
  #                                       config['SPATIAL']['Census_Block10_Centroids'] + '.shp')
  # block_centroids_clipped_layer = block_centroids_clipped_src.CreateLayer(config['SPATIAL']['Census_Block10_Centroids'],
  #                                                                   srs, ogr.wkbPoint)
  #
  # block_centroids_layer.Clip(la_clip_layer, block_centroids_clipped_layer)


def main(argv):

  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  import_and_prep_data(config)

if __name__ == '__main__':
    main(sys.argv[1:])

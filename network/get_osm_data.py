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

  base_long = -117.4
  base_lat = 33.4
  step = .5

  sub_network_segments = []
  # sub_network_segments = ['0.0.0.0','0.0.0.5','0.0.1.0','0.0.1.5',
  #                         '0.5.0.0','0.5.0.5','0.5.1.0','0.5.1.5',
  #                         '1.0.0.0','1.0.0.5','1.0.1.0','1.0.1.5',
  #                         '1.5.0.0','1.5.0.5','1.5.1.0','1.5.1.5']

  sub_network_segments = ['0.0.0.0','0.0.0.5','0.0.1.0','0.0.1.5']

  # Given a range of latitude and longitudes, loop through and download
  # the tiled OSM data
  # for long in frange(0.0, 1.5, step):
  long = 0.0
  for lat in frange(0.0, 1.5, step):
    latmin = round(decimal.Decimal(base_lat) + decimal.Decimal(lat), 1)
    latmax = round(decimal.Decimal(latmin) + decimal.Decimal(step), 1)

    longmin = round(decimal.Decimal(base_long) - decimal.Decimal(long), 1)
    longmax = round(decimal.Decimal(longmin) - decimal.Decimal(step), 1)

    longlatkey = str(long) + '.' + str(lat)

    print("Processing {} with min and max lat and long {} {} {} {}".format(longlatkey,
                                                                           str(latmax), str(latmin),
                                                                           str(longmin), str(longmax)))

    try:

      # Pull only drivable highways, primary and residential streets based on
      # https://wiki.openstreetmap.org/wiki/Key:highway
      greater_la_streets_box = ox.graph_from_bbox(latmax, latmin, longmin, longmax,
                                network_type='drive', simplify=True,
                                timeout=3600,
                                infrastructure='way["highway"~"motorway|trunk|primary|secondary|' \
                                'residential|motorway_link|trunk_link|primary_link"]')

      # G_projected = ox.project_graph(greater_la_streets_box)

      print ("   Saving to {}".format(config['SPATIAL']['CA_Street_Centerlines_OSM'] + longlatkey))

      ox.save_graph_shapefile(greater_la_streets_box, filename=config['SPATIAL']['CA_Street_Centerlines_OSM'] + longlatkey,
                         folder=config['SPATIAL']['BASE_STREET_PATH'])

    except ox.core.EmptyOverpassResponse:
      print("    No features found in request")

    except Exception as ex:
      print("    Exception happened of type {} with args {}".format(type(ex), ex.args))

  # Now merge the tiled OSM data into a single large file
  # We use the first of the subnetworks to grab the field definitions - little did
  # I know that not all the shapefiles have a consistent field list...
  sub_network_src = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'] \
                    ['CA_Street_Centerlines_OSM'] + \
                    '0.0.0.0' + '/edges/edges.shp'
  sub_network_ds = ogr.Open(sub_network_src)
  sub_network_spatial_ref = sub_network_ds.GetLayer().GetSpatialRef()

  with fiona.Env():
    input_for_schema = fiona.collection(config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'] \
                    ['CA_Street_Centerlines_OSM'] + \
                    '0.0.0.0' + '/edges/edges.shp', 'r')
    schema = input_for_schema.schema.copy()

    output = fiona.collection(config['SPATIAL']['BASE_STREET_PATH'] +
                        config['SPATIAL']['CA_Street_Centerlines_OSM'] + '.shp',
                        'w', 'ESRI Shapefile', schema)

  # Given a range of latitude and longitudes, loop through and download
  # the tiled OSM data
  for sub_network_key in sub_network_segments:

    print ("working on subnetwork {}".format(sub_network_key))

    sub_network_src = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'] \
                      ['CA_Street_Centerlines_OSM'] + \
                      sub_network_key + '/edges/edges.shp'

    if (os.path.exists(sub_network_src)):

      # Read the original Shapefile
      with fiona.Env():
        with fiona.collection(sub_network_src, 'r') as input:
          # The output has the same schema
          for elem in input:
           output.write({'properties': elem['properties'], 'geometry': mapping(shape(elem['geometry']))})

  # Now clip the OSM data and census blocks with the buffered LA Country polygon.
  la_clip_path = config['DEFAULT']['BASE_PATH_SPATIAL'] + config['SPATIAL']['LA_County_Buffered'] + '.shp'
  la_clip_path_src = ogr.Open(la_clip_path, 0)
  la_clip_layer = la_clip_path_src.GetLayer(0)

  print("About to clip Street Centerlines to buffered LA County area")

  california_streets = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Street_Centerlines_OSM'] + '.shp'
  california_streets_src = ogr.Open(california_streets, 0)
  california_streets_layer = california_streets_src.GetLayer(0)

  la_clipped_streets_src = driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                                                   config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'] + '.shp')
  la_clipped_streets_layer = la_clipped_streets_src.CreateLayer(config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'],
                                                                sub_network_spatial_ref, ogr.wkbLineString)

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

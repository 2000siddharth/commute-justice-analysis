import configparser, os, sys
from osgeo import ogr, osr
import decimal
import osmnx as ox

def frange(start, stop, step):
  i = start
  while i < stop:
    yield i
    i += step

def import_and_prep_data(config):

  driver = ogr.GetDriverByName('ESRI Shapefile')
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  # Grab street centerline from OSM and then we'll clip them at the ~20 mile LA County buffer
  # Tried of all of California but Docker kept killing the process - could have set oom-kill-false
  # But after downloading 200 MB of data, ran into 8 GB memory ceiling - moved to graph_from_bbox

  base_long = -117.4
  base_lat = 33.4
  step = .5

  sub_network_segments = []
  sub_network_segments = ['0.0.0.0','0.0.0.5','0.0.1.0','0.0.1.5',
                          '0.5.0.0','0.5.0.5','0.5.1.0','0.5.1.5',
                          '1.0.0.0','1.0.0.5','1.0.1.0','1.0.1.5',
                          '1.5.0.0','1.5.0.5','1.5.1.0','1.5.1.5']

  # Given a range of latitude and longitudes, loop through and download
  # the tiled OSM data
  for long in frange(0.0, 1.5, step):
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
                                  network_type='drive', simplify=False,
                                  timeout=3600,
                                  infrastructure='way["highway"~"motorway|trunk|primary|secondary|' \
                                  'residential|motorway_link|trunk_link|primary_link"]')

        G_projected = ox.project_graph(greater_la_streets_box)

        print ("   Saving to {}".format(config['SPATIAL']['CA_Street_Centerlines_OSM'] + longlatkey))

        ox.save_graph_shapefile(G_projected, filename=config['SPATIAL']['CA_Street_Centerlines_OSM'] + longlatkey,
                           folder=config['SPATIAL']['BASE_STREET_PATH'])

        sub_network_segments.append(longlatkey)


      except ox.core.EmptyOverpassResponse:
        print("    No features found in request")

  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)


  # Now merge the tiled OSM data into a single large file
  la_streets_osm_driver = ogr.GetDriverByName('ESRI Shapefile')
  la_streets_osm_src  = la_streets_osm_driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                            config['SPATIAL']['CA_Street_Centerlines_OSM'] + '.shp')
  la_streets_osm_layer = la_streets_osm_src.CreateLayer(
                            config['SPATIAL']['CA_Street_Centerlines_OSM'],
                            srs, ogr.wkbLineString)

  sub_network_src = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'] \
                    ['CA_Street_Centerlines_OSM'] + \
                    '0.0.0.0' + '/edges/edges.shp'
  sub_network_ds = ogr.Open(sub_network_src)
  sub_network_layer_defn =  sub_network_ds.GetLayer(0).GetLayerDefn()
  for i in range(sub_network_layer_defn.GetFieldCount()):
    la_streets_osm_layer.CreateField(sub_network_layer_defn.GetFieldDefn(i))

  for sub_network_key in sub_network_segments:

    print ("working on subnetwork {}".format(sub_network_key))

    sub_network_src = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'] \
                      ['CA_Street_Centerlines_OSM'] + \
                      sub_network_key + '/edges/edges.shp'
    if (os.path.exists(sub_network_src)):
      sub_network_ds = ogr.Open(sub_network_src)
      sub_network_layer = sub_network_ds.GetLayer(0)
      for sub_network_feature in sub_network_layer:
        la_streets_osm_layer.CreateFeature(sub_network_feature)

  la_streets_osm_layer = None
  la_streets_osm_src = None

  # Now clip the OSM data and census blocks with the buffered LA Country polygon.
  la_clip_path = config['DEFAULT']['BASE_PATH_SPATIAL'] + config['SPATIAL']['LA_County_Buffered'] + '.shp'
  la_clip_path_src = ogr.Open(la_clip_path, 0)
  la_clip_layer = la_clip_path_src.GetLayer(0)

  print("About to clip Street Centerlines to buffered LA County area")

  california_streets = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Street_Centerlines'] + '.shp'
  california_streets_src = ogr.Open(california_streets, 0)
  california_streets_layer = california_streets_src.GetLayer(0)

  la_clipped_streets_src = driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                                                   config['SPATIAL']['LA_Street_Centerlines'] + '.shp')
  la_clipped_streets_layer = la_clipped_streets_src.CreateLayer(config['SPATIAL']['LA_Street_Centerlines'],
                                                                srs, ogr.wkbLineString)

  california_streets_layer.Clip(la_clip_layer, la_clipped_streets_layer)

  print("About to clip Block Centroids to buffered LA County area")

  block_centroids = config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] + config['SPATIAL'][
    'Census_Block10_Centroids_Near_LA'] + '.shp'
  block_centroids_src = ogr.Open(block_centroids, 0)
  block_centroids_layer = block_centroids_src.GetLayer(0)

  block_centroids_clipped_src = driver.CreateDataSource(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                                        config['SPATIAL']['Census_Block10_Centroids'] + '.shp')
  block_centroids_clipped_layer = block_centroids_clipped_src.CreateLayer(config['SPATIAL']['Census_Block10_Centroids'],
                                                                    srs, ogr.wkbPoint)

  block_centroids_layer.Clip(la_clip_layer, block_centroids_clipped_layer)


def main(argv):

  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  import_and_prep_data(config)

if __name__ == '__main__':
    main(sys.argv[1:])

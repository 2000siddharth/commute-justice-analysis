import configparser, os, sys
from osgeo import ogr, osr

def import_and_prep_data(config):

  driver = ogr.GetDriverByName('ESRI Shapefile')
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  # Grab street centerline from OSM and then we'll clip them at the ~20 mile LA County buffer
  # Tried of all of California but Docker kept killing the process - could have set oom-kill-false
  # But after downloading 200 MB of data, ran into 8 GB memory ceiling - moved to graph_from_bbox
  # california_streets = ox.graph_from_place('California, USA', network_type='drive')
  # greater_la_streets_box = ox.graph_from_bbox(35.114, 33.514, -117.439, -119.316, network_type='drive', simplify=False,
  #                                         timeout=3600)
  # greater_la_streets_box = ox.graph_from_bbox(34, 33.7, -118.15, -118.5, network_type='drive', simplify=False,
  #                                         timeout=3600)
  # G_projected = ox.project_graph(greater_la_streets_box)

  # ox.save_graph_shapefile(G_projected, filename=config['SPATIAL']['CA_Street_Centerlines_OSM'],
  #                       folder=config['SPATIAL']['BASE_STREET_PATH'])

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

  if (1==2):
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

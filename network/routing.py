from osgeo import ogr

roadsrc = "/Users/cthomas/Development/Data/spatial/Network/streets/tl_2016_06000_roads.shp"
blocksrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10_centroids.shp"

roadnetwork = ogr.Open(roadsrc)
roadlayer  = roadnetwork.GetLayer(0)

blocknetwork = ogr.Open(blocksrc)
blocklayer  = blocknetwork.GetLayer(0)

print ('There are {}'.format(blocklayer.GetFeatureCount()))

for i in range(blocklayer.GetFeatureCount()):
    feature = blocklayer.GetFeature(i)
    geoid = feature.GetField("GEOID10")
    geometry = feature.GetGeometryRef()
    print (i, geoid, geometry.GetGeometryName())

for j in range(10):
    feature = roadlayer.GetFeature(j)
    name = feature.GetField("FULLNAME")
    geometry = feature.GetGeometryRef()
    print (j, name, geometry.GetGeometryName())



from osgeo import ogr
import configparser, os

# From http://gis.stackexchange.com/questions/7436/how-to-add-attribute-field-to-existing-shapefile-via-python-without-arcgis?rq=1
config = configparser.ConfigParser()
config.read(os.getcwd() + '/params.ini')
censussrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Census_Block10'] + '.shp'

census = ogr.Open(censussrc, 1)
censuslayer = census.GetLayer()

sa01 = ogr.FieldDefn('SA01', ogr.OFTInteger)
sa01_c = ogr.FieldDefn('SA01_CmDst', ogr.OFTInteger)
sa02 = ogr.FieldDefn('SA02', ogr.OFTInteger)
sa02_c = ogr.FieldDefn('SA02_CmDst', ogr.OFTInteger)
sa03 = ogr.FieldDefn('SA03', ogr.OFTInteger)
sa03_c = ogr.FieldDefn('SA03_CmDst', ogr.OFTInteger)
se01 = ogr.FieldDefn('SE01', ogr.OFTInteger)
se01_c = ogr.FieldDefn('SE01_CmDst', ogr.OFTInteger)
se02 = ogr.FieldDefn('SE02', ogr.OFTInteger)
se02_c = ogr.FieldDefn('SE02_CmDst', ogr.OFTInteger)
se03 = ogr.FieldDefn('SE03', ogr.OFTInteger)
se03_c = ogr.FieldDefn('SE03_CmDst', ogr.OFTInteger)
si01 = ogr.FieldDefn('SI01', ogr.OFTInteger)
si01_c = ogr.FieldDefn('SI01_CmDst', ogr.OFTInteger)
si02 = ogr.FieldDefn('SI02', ogr.OFTInteger)
si02_c = ogr.FieldDefn('SI02_CmDst', ogr.OFTInteger)
si03 = ogr.FieldDefn('SI03', ogr.OFTInteger)
si03_c = ogr.FieldDefn('SI03_CmDst', ogr.OFTInteger)

censuslayer.CreateField(sa01)
censuslayer.CreateField(sa01_c)
censuslayer.CreateField(sa02)
censuslayer.CreateField(sa02_c)
censuslayer.CreateField(sa03)
censuslayer.CreateField(sa03_c)
censuslayer.CreateField(se01)
censuslayer.CreateField(se01_c)
censuslayer.CreateField(se02)
censuslayer.CreateField(se02_c)
censuslayer.CreateField(se03)
censuslayer.CreateField(se03_c)
censuslayer.CreateField(si01)
censuslayer.CreateField(si01_c)
censuslayer.CreateField(si02)
censuslayer.CreateField(si02_c)
censuslayer.CreateField(si03)
censuslayer.CreateField(si03_c)

census = None


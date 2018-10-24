import csv
from census.origin_destination_db import OriginDestinationDB
import configparser, os

config = configparser.ConfigParser()
config.read(os.getcwd() + '/params.ini')
odsrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Block_Centroid_Intersections'] + '.csv'

odb = OriginDestinationDB()

n = 0
with open(odsrc, mode='r') as infile:
  reader = csv.reader(infile, delimiter='\t')
  next(reader)
  for row in reader:
    n = n + 1
    if (n % 10000) == 0:
      print("We're at record {}".format(str(n)))
      print ("Row {}".format(row[:1]))
      odb.commit()
    insert_values = (row[0], row[1].replace("'", ""))
    insert = "INSERT INTO block_centroid_intersection values (?,?)"
    odb.insert(insert, insert_values)
odb.commit()

odsrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Street_Segment_Block_Centroid_Connectors'] + '.csv'

n = 0
with open(odsrc, mode='r') as infile:
  reader = csv.reader(infile, delimiter='\t')
  next(reader)
  for row in reader:
    n = n + 1
    if (n % 10000) == 0:
      print("We're at record {}".format(str(n)))
      print ("Row {}".format(row[:1]))
      odb.commit()
    insert_values = (row[0], row[1].replace("'", ""))
    insert = "INSERT INTO street_segment_block_centroid_connector values (?,?)"
    odb.insert(insert, insert_values)
odb.commit()

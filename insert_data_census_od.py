import csv
from census.origin_destination_db import OriginDestinationDB
import configparser, os

config = configparser.ConfigParser()
config.read(os.getcwd() + '/params.ini')
odsrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Origin_Destination'] + '.csv'

odb = OriginDestinationDB()

n = 0
with open(odsrc, mode='r') as infile:
  reader = csv.reader(infile)
  next(reader)
  for row in reader:
    n = n + 1
    if (n % 10000) == 0:
      print("We're at record {}".format(str(n)))
      print ("Row {}".format(row[:11]))
      odb.commit()
    insert = "INSERT INTO origindestination values (?,?,?,?,?,?,?,?,?,?,?,?)"
    odb.insert(insert, row[:12])
odb.commit()

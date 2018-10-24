import csv
from census.xwalk_db import XWalkDB
import configparser, os

odsrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Xwalk'] + '.csv'

odb = XWalkDB()

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
    insert = "INSERT INTO xwalk values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    odb.insert(insert, row[:40])

    

import csv
from census.origin_destination_db import OriginDestinationDB

odsrc = "/Users/cthomas/Development/Data/Census/ca_od_main_JT00_2014.csv"

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
    

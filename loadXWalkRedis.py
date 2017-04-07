import csv, io
import pandas as pd
import redis
import time

def load(fields, pdtDict):
  start_time = time.time()
  redIS = redis.Redis()
  pipe = redIS.pipeline()
  n = 1
  for key in pdtDict.keys():
    n = n + 1
    if (n % 64) == 0:
      pipe.execute()
      pipe = redIS.pipeline()
      print ("We have n of {}".format(str(n)))

    blockDict = dict(zip(fields, pdtDict[key]))
#    print("We have key {} with values {}".format(key, blockDict)) 
    pipe.hmset("block:" + str(key),blockDict)
  pipe.execute()
  print("--- %s seconds ---" % (time.time() - start_time))

def simple_loop_dictionary_walk():
  start_time = time.time()
  dctWalks = {}
  with open('ca_xwalk.csv', 'r') as walk:
    reader = csv.reader(walk, delimiter = ",")
    fieldnames = next(reader)
    for line in reader:
      k, v = line[0], line[1:]
#      print ("we have key {} with values {}".format(k, v))
      dctWalks[k] = list(map(str, v))
  print("--- %s seconds ---" % (time.time() - start_time))
  return fieldnames, dctWalks

# Not using - this method was dveloped here, but doesn't work as i have
# coded it - confused column cound for row count.
def optimized_dictionary_walk():
  start_time = time.time()
  cols = pd.read_csv(io.open('ca_xwalk.csv'), sep='\s+', usecols=[0], header=None)[0].values
  df = pd.read_csv(io.open('ca_xwalk.csv'), sep='\s+', header=None, usecols = list(range(1, len(cols)+1)), names = cols)
  print("--- %s seconds ---" % (time.time() - start_time))
  return df.to_dict()

fields, dictWalks = simple_loop_dictionary_walk()

load(fields, dictWalks)

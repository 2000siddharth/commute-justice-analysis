import zipfile, os, shutil
from urllib.request import urlopen, HTTPError

"""Download and extract all TIGER street centerlines from california"""
streeturlbase = "https://www2.census.gov/geo/tiger/TIGER2016/ROADS/"
streeturlfile = "tl_2016_06[00]_roads.zip"

for i in range(100,120):
  streeturlfilename = streeturlfile.replace('[00]', (str(i)).rjust(2,'0'))
  print (streeturlbase + streeturlfilename + '\n')
  try:
    response = urlopen(streeturlbase + streeturlfilename)
    with open(streeturlfilename, 'wb') as output:
      output.write(response.read())
    zip_ref = zipfile.ZipFile(streeturlfilename, 'r')
    zip_ref.extractall('streets')
    zip_ref.close()
    os.remove(streeturlfilename)
  except HTTPError as e:
    print (e.code)

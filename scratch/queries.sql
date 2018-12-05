# Find information about residents that commute to RANDs block
select h_geocode , sum(s000)  as residentcount , max(se01), max(se02), max(se03)
from origindestination where w_geocode = '060377019023015'  group by h_geocode
order by sum(s000) desc

# Grab the commute data
select od.h_geocode, SA01, SA02, SA03, SE01, SE02, SE03, SI01, SI02, SI03,
          cd.distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode


select Code, total_distance, people, avg_distance from(
select  'SA01' As Code, SUM(CAST(SA01 AS INTEGER)*IFNULL(cd.distance,0)) AS total_distance,
SUM(CAST(SA01 AS INTEGER)) AS People,
SUM(CAST(SA01 AS INTEGER)*IFNULL(cd.distance,0)) /SUM(CAST(SA01 AS INTEGER))  AS Avg_distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode
where od.w_geocode = '060377019023015'
AND CAST(od.SA01 AS INTEGER) > 0
union
select   'SA02' As Code, SUM(CAST(SA02 AS INTEGER)*IFNULL(cd.distance,0)) AS total_distance,
SUM(CAST(SA02 AS INTEGER)) AS People,
SUM(CAST(SA02 AS INTEGER)*IFNULL(cd.distance,0)) /SUM(CAST(SA02 AS INTEGER))  AS Avg_distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode
where od.w_geocode = '060377019023015'
AND CAST(od.SA02 AS INTEGER) > 0
union
select  'SA03' As Code,  SUM(CAST(SA03 AS INTEGER)*IFNULL(cd.distance,0)) AS total_distance,
SUM(CAST(SA03 AS INTEGER)) AS People,
SUM(CAST(SA03 AS INTEGER)*IFNULL(cd.distance,0)) /SUM(CAST(SA03 AS INTEGER))  AS Avg_distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode
where od.w_geocode = '060377019023015'
AND CAST(od.SA03 AS INTEGER) > 0
union
select  'SE01' As Code,  SUM(CAST(SE01 AS INTEGER)*IFNULL(cd.distance,0)) AS total_distance,
SUM(CAST(SE01 AS INTEGER)) AS People,
SUM(CAST(SE01 AS INTEGER)*IFNULL(cd.distance,0)) /SUM(CAST(SE01 AS INTEGER))  AS Avg_distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode
where od.w_geocode = '060377019023015'
AND CAST(od.SE01 AS INTEGER) > 0
union
select  'SE02' As Code,  SUM(CAST(SE02 AS INTEGER)*IFNULL(cd.distance,0)) AS total_distance,
SUM(CAST(SE02 AS INTEGER)) AS People,
SUM(CAST(SE02 AS INTEGER)*IFNULL(cd.distance,0)) /SUM(CAST(SE02 AS INTEGER))  AS Avg_distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode
where od.w_geocode = '060377019023015'
AND CAST(od.SE02 AS INTEGER) > 0
union
select  'SE03' As Code,  SUM(CAST(SE03 AS INTEGER)*IFNULL(cd.distance,0)) AS total_distance,
SUM(CAST(SE03 AS INTEGER)) AS People,
SUM(CAST(SE03 AS INTEGER)*IFNULL(cd.distance,0)) /SUM(CAST(SE03 AS INTEGER))  AS Avg_distance
from origindestination od join commute_distances cd on od.h_geocode = cd.h_geocode
where od.w_geocode = '060377019023015'
AND CAST(od.SE03 AS INTEGER) > 0)
order by Code


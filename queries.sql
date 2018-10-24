# Find information about residents that commute to RANDs block
select h_geocode , sum(s000)  as residentcount , max(se01), max(se02), max(se03)
from origindestination where w_geocode = '060377019023015'  group by h_geocode
order by sum(s000) desc
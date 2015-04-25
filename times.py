# data is in 18191dates.pkl
# typ,data = imap.uid("FETCH",str(i),"(BODY[HEADER.FIELDS (DATE)])")
# last uid 
# >>> uids[18190]
# '28119'

# http://arrow.readthedocs.org/en/latest/

import arrow
from dateutil import tz
import datetime
import pickle

# all_datestrings = ['Date: Fri, 24 Apr 2015 17:05:01 -0400',\
# 				   'Date: Mon, 6 Apr 2015 16:12:00 +0000 (UTC)',\
# 				   'Date: Mon, 6 Apr 2015 10:38:04 -0400 (EDT)',\
# 				   'Date: Sun, 01 Mar 2015 20:37:06 -0500']

def is_daylight_savings(arrow):
	if arrow.month >= 4 and arrow.month <= 10:
		return True
	if arrow.month <= 2 or arrow.month >= 11:
		return False
	# month is march
	return arrow.day >= 8

def convert_from_utc_with_bool(arrow, ids):
	if ids:
		return arrow.replace(hours=-4)
	else:
		return arrow.replace(hours=-5)

def convert_from_utc(arrow):
	ids = is_daylight_savings(arrow)
	return convert_from_utc_with_bool(arrow, ids)

def is_utc(arrow):
	if arrow.tzinfo == None:
		return True
	return arrow.tzinfo.utcoffset(arrow) == datetime.timedelta(0)

all_tuples_dict = {}
all_days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
for day in all_days:
	for hour_num in range(0,24):
		hour_str = str(hour_num)
		all_tuples_dict[(day, hour_str)] = 0

file = open("18191dates.pkl","rb")
all_datestrings = pickle.load(file)
file.close()

all_datestrings = [a.replace("GMT", "+0000") for a in all_datestrings]
all_datestrings = [a.replace("EDT", "-0400") for a in all_datestrings]
all_datestrings = [a.replace("EST", "-0500") for a in all_datestrings]
all_datestrings = [a.replace("UTC", "+0000") for a in all_datestrings]
all_datestrings = [a.replace("UT", "+0000") for a in all_datestrings]
all_datestrings = filter(lambda a: a != '', all_datestrings)

i = 0
for datestring in all_datestrings:
	print i
	just_date = datestring.split(": ")[1]
	my_arrow = arrow.get(just_date,"ddd, D MMM YYYY H:m:s Z")
	if is_utc(my_arrow):
		my_arrow = convert_from_utc(my_arrow)
	day = my_arrow.format(fmt="ddd")
	hour = str(my_arrow.hour)
	my_tuple = (day, hour)
	all_tuples_dict[my_tuple] += 1
	i += 1


{('Sun', '9'): 49, ('Thu', '14'): 29, ('Sun', '12'): 132, ('Wed', '11'): 40, ('Mon', '4'): 5, ('Tue', '18'): 294, ('Tue', '4'): 14, ('Thu', '3'): 5, ('Fri', '5'): 8, ('Sun', '16'): 182, ('Mon', '5'): 5, ('Sat', '16'): 99, ('Thu', '17'): 99, ('Thu', '2'): 7, ('Wed', '16'): 118, ('Fri', '4'): 9, ('Mon', '21'): 404, ('Fri', '10'): 34, ('Sat', '2'): 12, ('Tue', '21'): 416, ('Mon', '2'): 35, ('Tue', '2'): 24, ('Sun', '13'): 170, ('Thu', '1'): 48, ('Mon', '13'): 43, ('Fri', '3'): 8, ('Tue', '13'): 30, ('Mon', '3'): 7, ('Fri', '13'): 50, ('Sat', '23'): 215, ('Thu', '0'): 94, ('Sun', '19'): 239, ('Fri', '2'): 12, ('Mon', '19'): 321, ('Wed', '8'): 27, ('Mon', '14'): 62, ('Thu', '10'): 29, ('Fri', '20'): 167, ('Sat', '5'): 3, ('Mon', '0'): 195, ('Sun', '22'): 360, ('Tue', '14'): 39, ('Wed', '18'): 272, ('Tue', '0'): 71, ('Thu', '23'): 258, ('Fri', '1'): 26, ('Wed', '22'): 320, ('Wed', '9'): 38, ('Fri', '14'): 60, ('Mon', '1'): 53, ('Sat', '12'): 126, ('Sun', '2'): 8, ('Thu', '13'): 32, ('Wed', '12'): 58, ('Tue', '19'): 258, ('Fri', '23'): 196, ('Sat', '7'): 14, ('Wed', '21'): 437, ('Tue', '9'): 29, ('Sat', '8'): 31, ('Sun', '3'): 5, ('Sun', '17'): 205, ('Thu', '19'): 317, ('Sat', '17'): 149, ('Thu', '16'): 58, ('Wed', '17'): 123, ('Mon', '20'): 309, ('Sun', '0'): 116, ('Tue', '20'): 369, ('Fri', '15'): 35, ('Wed', '4'): 10, ('Sat', '19'): 123, ('Sun', '10'): 55, ('Mon', '10'): 31, ('Sat', '14'): 47, ('Sat', '1'): 21, ('Tue', '7'): 18, ('Tue', '10'): 26, ('Sun', '1'): 89, ('Wed', '14'): 56, ('Mon', '23'): 265, ('Fri', '12'): 70, ('Wed', '5'): 9, ('Fri', '21'): 191, ('Tue', '23'): 219, ('Fri', '19'): 203, ('Sun', '6'): 3, ('Mon', '15'): 133, ('Fri', '22'): 304, ('Sun', '21'): 365, ('Tue', '15'): 42, ('Wed', '19'): 300, ('Wed', '6'): 21, ('Fri', '18'): 89, ('Thu', '20'): 433, ('Sat', '3'): 3, ('Tue', '5'): 8, ('Sat', '21'): 131, ('Sun', '7'): 20, ('Thu', '9'): 42, ('Sat', '13'): 109, ('Wed', '7'): 27, ('Mon', '16'): 154, ('Thu', '12'): 21, ('Wed', '13'): 53, ('Tue', '16'): 99, ('Sun', '4'): 2, ('Thu', '8'): 21, ('Wed', '20'): 325, ('Fri', '8'): 28, ('Wed', '0'): 99, ('Sun', '14'): 149, ('Sat', '4'): 3, ('Thu', '18'): 205, ('Sat', '10'): 131, ('Mon', '8'): 10, ('Tue', '3'): 9, ('Thu', '15'): 55, ('Sun', '5'): 5, ('Wed', '10'): 34, ('Fri', '9'): 28, ('Wed', '1'): 34, ('Mon', '9'): 29, ('Sun', '11'): 114, ('Fri', '17'): 103, ('Mon', '11'): 26, ('Sat', '15'): 58, ('Tue', '11'): 33, ('Wed', '15'): 84, ('Wed', '2'): 9, ('Sat', '6'): 17, ('Fri', '11'): 35, ('Mon', '22'): 374, ('Tue', '8'): 27, ('Thu', '7'): 28, ('Tue', '1'): 19, ('Tue', '22'): 376, ('Sat', '18'): 134, ('Wed', '3'): 8, ('Mon', '12'): 53, ('Sun', '20'): 329, ('Tue', '12'): 22, ('Thu', '6'): 12, ('Sat', '22'): 218, ('Sun', '8'): 23, ('Thu', '21'): 385, ('Sat', '20'): 164, ('Mon', '6'): 15, ('Sun', '18'): 186, ('Sat', '0'): 78, ('Mon', '18'): 240, ('Tue', '6'): 21, ('Sat', '9'): 53, ('Thu', '5'): 4, ('Mon', '17'): 115, ('Thu', '11'): 31, ('Fri', '16'): 86, ('Fri', '7'): 19, ('Sun', '23'): 396, ('Tue', '17'): 203, ('Fri', '0'): 105, ('Mon', '7'): 20, ('Thu', '22'): 317, ('Wed', '23'): 300, ('Thu', '4'): 7, ('Sun', '15'): 178, ('Fri', '6'): 24, ('Sat', '11'): 72}
18190


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

file = open("18191dates.pkl","rb")
all_datestrings = pickle.load(file)
file.close()

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



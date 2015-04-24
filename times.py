all_tuples_dict = {}
all_days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
for day in all_days:
	for hour_num in range(0,24):
		hour_str = str(hour_num)
		all_tuples_dict[(day, hour_str)] = 0

all_datestrings = ['Date: Fri, 24 Apr 2015 17:05:01 -0400',\
				   'Date: Mon, 6 Apr 2015 16:12:00 +0000 (UTC)',\
				   'Date: Mon, 6 Apr 2015 10:38:04 -0400 (EDT)',\
				   'Date: Sun, 01 Mar 2015 20:37:06 -0500']
for datestring in all_datestrings:
	split_date = datestring.split()
	day_hour_tuple = (split_date[1], split_date[5].split(":")[0])
	all_tuples_dict[day_hour_tuple] += 1


import arrow
from dateutil import tz

just_date = datestring.split(": ")[1]
arrow.get(just_date,"ddd, D MMM YYYY HH:mm:ss Z")
# save the day of the week

# if utc, figure out based on time of year whether we should convert to 
# edt or est

# data is in 18191dates.pkl
# typ,data = imap.uid("FETCH",str(i),"(BODY[HEADER.FIELDS (DATE)])")
# last uid 
# >>> uids[18190]
# '28119'


# http://arrow.readthedocs.org/en/latest/
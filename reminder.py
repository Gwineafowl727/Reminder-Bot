from datetime import date, datetime, timedelta
import re
from replit import db

def addReminder(date: str, time: str, text: str, user: int, ctx) -> None:
 	# Add a reminder to the database.
	num = 1
	while f"{user}_{num}" in db.keys():
		num += 1
	key = f"{user}_{num}"
	value = [date, time, text]
	db[key] = value
	return True

def deleteReminder(num: int, user: str) -> bool:
 	# Delete a reminder.
	reminders = viewReminders(user)
	val = reminders[num]
	if num in reminders.keys():
		for key in db.keys():
			if db[key] == val and user in key:
				del db[key]
				return True

def viewReminders(user: str) -> dict:
	# Generate a list of reminders for viewing.
	res = {}
	num = 1
	for key in db.keys():
		if user in key:
			res[num] = db.get(key)
			num += 1
	return sortReminders(res)

def getDatetimeFormat(date, time):
	
	# Both Regexes developed on pythex.org
	dateRegex = re.compile(r'''
		(0?[1-9]|1[0-2])				# month (01 - 12)
	    /								# separator
	 	(0?[1-9]|[1-2][0-9]|3[01])		# day (01 - 31)
	    /								# separator
		([0-9]{4})						# years (1000 - 2999)
    ''', re.VERBOSE)
	
	timeRegex = re.compile(r'''
		(0?[1-9]|1[0-2])				# hour from 0-9 or 10-12
	 	:								# separator
	  	([0-5][0-9])					# minutes from 0-59
	   	\s?[aApP][mM]					# AM or PM (case insensitive)
	''', re.VERBOSE)
	
	month, day, year = dateRegex.search(date).groups()
	hour, minute = timeRegex.search(time).groups()
		
	if 1 <= int(hour) <= 11 and time[-2:] == 'PM':
		hour = int(hour) + 12
	elif int(hour) == 12 and time[-2:] == 'AM':
		hour = 0
	
	return datetime(int(year), int(month), int(day), int(hour), int(minute))

def sortReminders(reminders: dict) -> dict:
	# Return the user's reminders in chronological order
	res = {}
	datesAndTimes = []
	
	for i in range(len(reminders)):
		date = reminders[i+1][0]
		time = reminders[i+1][1]
		
		dt = getDatetimeFormat(date, time)
		
		datesAndTimes.append((dt, i+1))

	# Sorting list by specified index: https://www.geeksforgeeks.org/python-sort-list-of-list-by-specified-index/
	datesAndTimes = sorted(datesAndTimes, key=lambda datesAndTimes: datesAndTimes[0])
	for num, item in enumerate(datesAndTimes, 1):
		res[num] = reminders[datesAndTimes[num-1][1]]
	return res
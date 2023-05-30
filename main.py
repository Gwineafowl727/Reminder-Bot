from datetime import date, datetime, timedelta
import discord
from discord.ext import tasks, commands
import os
import re
import reminder
from replit import db

# Bot invite URL generated on Discord developer portal:
# https://discord.com/api/oauth2/authorize?client_id=1073086536863723616&permissions=8&scope=bot\

# Primary source for Discord bot setup code and command syntax:
# https://discordpy.readthedocs.io/en/stable/quickstart.html

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.messages = True

description = "A bot built to remind people. Please have direct messages enabled in order to be pinged of your reminders."

help_command = commands.DefaultHelpCommand(
	no_category = 'Commands'
)

bot = commands.Bot(
	command_prefix="!",
	description=description,
	intents=intents,
	help_command = help_command
)

info = """
!r add <date> <time> <text> - Add a reminder containing text. Ping user at date. Date must be dd/mm/yyyy format, time must be AM/PM format on a 12 hour clock.
!r clear (all) - Delete all of the user's reminders in the database. Add "all" to delete everyone's reminders.
!r delete <num> - Delete the reminder at that number. Can only delete if you added the reminder.
!r list - View a list of all reminders that you have created.
"""

# Both Regexes developed on pythex.org
dateRegex = re.compile(r'''
	(0?[1-9]|1[0-2])				# month (01 - 12)
    /								# separator
 	(0?[1-9]|[1-2][0-9]|3[01])		# day (01 - 31)
    /								# separator
	([0-9]{4})						# years (1000 - 2999)
''', re.VERBOSE)

timeRegex = re.compile(r'''(
	(\A[1-9]|1[0-2])				# hour from 0-9 or 10-12
 	:								# separator
  	([0-5][0-9])					# minutes from 0-59
   	(\s?[aApP][mM])					# AM or PM (case insensitive)
)''', re.VERBOSE)

# Check if date is valid
def checkDate(date) -> bool:
	# Month : Days
	months = {
		'01' : 31,
	    '02' : 28,
	    '03' : 31,
	    '04' : 30,
	    '05' : 31,
	    '06' : 30,
	    '07' : 31,
	    '08' : 31,
	    '09' : 30,
	    '10' : 31,
	    '11' : 30,
	    '12' : 31
	    }
	
	if not dateRegex.search(date):
		return False
	
	month, day, year = dateRegex.search(date).groups()

	# Check if leap year
	if int(year) % 400 == 0 or (int(year) % 100 !=0 and int(year) % 4 == 0):
		months['02'] = 29

	# Format single digit months into two digits
	if len(month) == 1 and not month.startswith('0'):
		month = '0' + month

	# Format double digit days (9 or less) into one digit
	if len(day) == 2 and day.startswith('0'):
		day = day[1:]

	return int(day) <= months[month]

@bot.command(description="Add a reminder.")
async def r(ctx: str, *, arg: str = commands.parameter(description=description, default=info)):
	arg = arg.split()
	cmd = arg[0]
	user = ctx.author.id
	
	if cmd.lower() == "add":
		# Add a reminder, run through checks
		if len(arg) < 4:
			await ctx.send("Incorrect format. Type \"!help r\" for info.")
			return
			
		date = arg[1]
		time = arg[2]
		
		# Check if date is valid
		if checkDate(date):
			# Check if time is valid
			if not time.lower().endswith("m"):
				time += " " + arg[3].upper()
				arg[2] = time
				arg.pop(3)
			else:
				time = time[:-2] + " " + time[-2:].upper()
				arg[2] = time
				
			if timeRegex.search(time):
				# Create the text portion and store the reminder in database
				text = " ".join(arg[arg.index(time)+1:])
				reminder.addReminder(date, time, text, user, ctx)
				await ctx.send("Reminder successfully added")
		
			else:
				await ctx.send("Invalid time")
		
		else:
			await ctx.send("Invalid date")
					
	elif cmd.lower() == "delete":
		# Delete reminder by chronological index
		if reminder.deleteReminder(int(arg[1]), str(user)):
			await ctx.send(":crab: Reminder successfully deleted :crab:")
		else:
			await ctx.send("Not a valid choice")
		
	elif cmd.lower() == "list":
		"""
		Reminders will be stored in the following format:
		Keys: Number (starting at 1)
		Values: Reminder, user, date, time
		"""
		reminders = reminder.viewReminders(str(user))
		if not reminders:
			await ctx.send(f"<@{user}> has no reminders")
			return
		await ctx.send(f"<@{user}>'s reminders:")
		
		# Formatting for sending in channel
		res = '```\n'
		for i in range(len(reminders)):
			text = reminders[i+1][2]
			date = reminders[i+1][0]
			time = reminders[i+1][1]
			res += (
				f"{i+1}. {text}\n"
				f"{date} {time}\n"
				"\n"
			)
		res += '```'
		await ctx.send(res)
		
	elif cmd.lower() == "clear":
		# Clears all of the user's reminders; adding "all" will clear all users' reminders
		if len(arg) > 1 and arg[1].lower() == "all":
			# Replit database use and syntax: https://docs.replit.com/hosting/databases/replit-database
			for key in db.keys():
				del db[key]
			await ctx.send("Successfully cleared all reminders")
		else:
			for key in db.keys():
				if str(user) in key:
					del db[key]
			await ctx.send("Successfully cleared your reminders.")
		
	else:
		await ctx.send("Not a valid choice. Type \"!help r\" for info.")

@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandNotFound):
		await ctx.send(f'No command called "{str(ctx.message.content)[1:]}" found.')

# Background timer
# Task loop help: https://github.com/Rapptz/discord.py/blob/master/examples/background_task.py
@tasks.loop(seconds = 30)
async def checkTime():
	# Get current datetime
	# Datetime module help: https://www.geeksforgeeks.org/python-datetime-module/
	today = date.today()
	today = today.strftime("%m/%d/%Y")
	timeRN = (datetime.now() + timedelta(hours=-7)).strftime("%I:%M %p")
	currentDateTime = reminder.getDatetimeFormat(today, timeRN)
	
	# Check datetime with each item in database
	temp = []
	for key in db.keys():
		rDate = db.get(key)[0]
		rTime = db.get(key)[1]
		dt = reminder.getDatetimeFormat(rDate, rTime)
		if dt <= currentDateTime:
			temp.append(key)
	
	# Ping users if database
	for k in temp:
		id = k[:k.index("_")]
		rText = db.get(k)[2]
		user = bot.get_user(int(id))
		await user.send(f"<@{id}>, this is your reminder to **{rText}**.")

	# Delete keys
	for k in temp:
		del db[k]

@bot.event
async def on_ready():
	print(f'Logged in as {bot.user} (ID: {bot.user.id})')
	print("------\n")
	checkTime.start()

# Discord bot token stored as Replit secret
bot.run(os.getenv("TOKEN"))
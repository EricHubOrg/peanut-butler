from dotenv import load_dotenv
import os, json, logging, asyncio
import datetime, dateparser, discord, re

from utils import *

load_dotenv()
logging.basicConfig(level=logging.INFO)
dateparser_settings = {'PREFER_DATES_FROM': 'future'}

def retrieve_item(lst, value, key='id', remove=False):
	# returns item from list of dictionaries, and remove it optionally. If not found, returns None
	if remove:
		item = None
		lst[:] = [d for d in lst if d[key] != value or (item := d) and False]
	else:
		item = next((d for d in lst if d.get(key) == value), None)
	return item

async def retrieve_reminder_from_file(value, key='id', remove=False, type='reminders', return_data=False):
	# returns reminder from file, and remove it optionally. If not found, returns None
	f = await read_from_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json')
	data = json.loads(f)
	rem = retrieve_item(data[type], key, value, remove)
	if remove:
		await write_to_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json', json.dumps(data))
	if return_data:
		return rem, data
	else:
		return rem

async def send_reminder(bot, reminder_id):
	# send reminder to channel
	rem = await retrieve_reminder_from_file(reminder_id)
	if not rem: return
	channel = bot.get_channel(rem['channel_id'])
	if rem['mention']:
		if rem['mention'] == 'you':
			author = bot.get_user(rem['author_id'])
			await channel.send(f'{author.mention} {rem["message"]}')
		else:
			await channel.send(f'{rem["mention"]} {rem["message"]}')
	else:
		await channel.send(f'Reminder: {rem["message"]}')

async def activate_saved_reminders(scheduler, bot):
	# activate all saved reminders
	f = await read_from_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json')
	reminders = json.loads(f)['reminders']
	for rem in reminders:
		not_args = ('author_id', 'channel_id', 'message', 'mention', 'activation_date')
		rem_kwargs = {key:value for key, value in rem.items() if key not in not_args}
		scheduler.add_job(send_reminder, **rem_kwargs, args=[bot, rem['id']], tags=['reminder'])

async def clear_open_reminders():
	# remove all open reminders from file
	f = await read_from_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json')
	data = json.loads(f)
	data['open_reminders'] = []
	await write_to_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json', json.dumps(data))

async def pop_open_reminder(reminder_id):
	# remove open reminder from file and return it
	return await retrieve_reminder_from_file(reminder_id, remove=True, type='open_reminders')

def parse_interval(string):
	# preprocessing
	string = string.lower()
	replacements = {
		"every minute": "every 1 minutes",
		"every hour": "every 1 hours",
		"every day": "every 1 days",
		"every week": "every 1 weeks",
		"every monday": "every 1 monday",
		"every tuesday": "every 1 tuesday",
		"every wednesday": "every 1 wednesday",
		"every thursday": "every 1 thursday",
		"every friday": "every 1 friday",
		"every saturday": "every 1 saturday",
		"every sunday": "every 1 sunday"
	}
	
	for original, replacement in replacements.items():
		string = string.replace(original, replacement)

	# Patterns for parsing
	patterns = {
		"interval_simple": re.compile(r'^every\s*(?P<value>\d+)?\s*(?P<unit>minute|hour|day|week)s?\s*(?:at\s*(?P<hour>\d{2}):\s*(?P<minute>\d{2}))?$', re.IGNORECASE),
		"cron_weekdays_with_time": re.compile(r'^every\s*(?:\d+\s*)?(?P<day_of_week>(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:,\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))*)s?\s*(?:at\s*(?P<hour>\d{2}):\s*(?P<minute>\d{2}))?$', re.IGNORECASE),
		"cron_month_day": re.compile(r'^every\s*(?P<month>(?:(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:,\s*)?)+|month)\s*(?:on\s*)?(?P<day>\d+)(?:\s*at\s*(?P<hour>\d{2}):\s*(?P<minute>\d{2}))?$', re.IGNORECASE)
	}

	# Month mapping for conversion from name to number
	month_mapping = {
		"january": "1", "february": "2", "march": "3", "april": "4", 
		"may": "5", "june": "6", "july": "7", "august": "8", 
		"september": "9", "october": "10", "november": "11", "december": "12",
		"month": "1-12"
	}

	# Weekday mapping for conversion from name to number
	weekday_mapping = {
		"monday": "0", "tuesday": "1", "wednesday": "2", "thursday": "3", 
		"friday": "4", "saturday": "5", "sunday": "6"
	}

	for pattern_name in patterns:
		pattern = patterns[pattern_name]
		match = pattern.search(string)
		if match:
			result = match.groupdict()
			
			# Convert month names to numbers if present
			if 'month' in result:
				# Split the month string by comma and map each month to its corresponding number
				months = result['month'].split(',')
				result['month'] = ','.join([month_mapping[m.strip().lower()] for m in months])
			
			# Convert weekday names to numbers if present
			if 'day_of_week' in result:
				result['day_of_week'] = ','.join([weekday_mapping[dw.strip().lower()] for dw in result['day_of_week'].split(',')])
			
			if "interval" in pattern_name:
				result['trigger'] = 'interval'
			else:
				result['trigger'] = 'cron'
			return result
	return {}

async def complete_open_reminder(bot, reminder_id, emoji=None, user_input=None, rem=None, data=None):
	if not rem:
		rem, data = await retrieve_reminder_from_file(reminder_id, type='open_reminders', return_data=True)
	step = rem['step']
	thread = bot.get_channel(rem['thread_id'])

	async def q_info_exists():
		# check if there is already a question info message
		if rem['q_info_id']:
			try:
				await thread.fetch_message(rem['q_info_id'])
				return True
			except discord.errors.NotFound:
				return False
		return False
	
	def get_q_info_text():
		# get text for question info message
		if step == 0:
			return f'{rem["start_with"]}Et faré algunes preguntes, `respon` o `reacciona` \
					a cada missatge. En qualsevol moment pots cancel·lar reaccionant al missatge de creació amb ❌.'
		elif step == 2:
			return f'{rem["start_with"]}For example:\nevery day at 14:30\nevery 2 weeks\n\
					every Monday, Wednesday, Friday at 00:00\nevery June, July 4 at 12:00\nevery month on 14 at 12:00'
		elif step in (3, 4, 5):
			return f'{rem["start_with"]}For example:\ntomorrow at 14:30\nFriday at 19:45\nin 3 days at 09:00\n\
					2023-08-12 at 00:00\nApril 6 at 12:00'

	async def mention_question():
		# send question for mention
		author = await bot.fetch_user(rem['author_id'])
		if author.guild_permissions.mention_everyone:
			# user has mention permissions
			q_message = await thread.send(f"{rem['start_with']}Qui vols que es mencioni en el recordatori?\n\
								1️⃣ Tu\n2️⃣ @everyone\n3️⃣ @here\n4️⃣ Ningú")
			await q_message.add_reaction('1️⃣')
			await q_message.add_reaction('2️⃣')
			await q_message.add_reaction('3️⃣')
			await q_message.add_reaction('4️⃣')
		else:
			# user doesn't have mention permissions
			q_message = await thread.send(f"{rem['start_with']}Vols que se't mencioni en el recordatori?\n\
								✅ Sí\n❌ No")
			await q_message.add_reaction('✅')
			await q_message.add_reaction('❌')
		rem['q_message_id'] = q_message.id

	async def send_confirmation_message():
		# send confirmation message
		if rem['trigger'] == 'date':
			# on 'YYYY-MM-DD HH:MM'
			end_with = 'on ' + rem['run_date']
		else:
			if rem['trigger'] == 'interval':
				# every 'AMOUNT' 'UNIT', 
				end_with = 'every '
				for key in rem:
					if key in ('weeks', 'days', 'hours', 'minutes', 'seconds'):
						end_with += f'{rem[key]} {key}, '
						break
			elif rem['trigger'] == 'cron':
				end_with = 'every '
				if 'day_of_week' in rem:
					# every 'DAY_OF_WEEK', 
					mapping = {'0': 'Monday', '1': 'Tuesday', '2': 'Wednesday', '3': 'Thursday', '4': 'Friday', '5': 'Saturday', '6': 'Sunday'}
					end_with += f'{mapping[rem["day_of_week"]]}, '
				elif 'month' in rem:
					# every 'MONTH' 'DAY', 
					mapping = {'1': 'January', '2': 'February', '3': 'March', '4': 'April', '5': 'May', '6': 'June',
								'7': 'July', '8': 'August', '9': 'September', '10': 'October', '11': 'November', '12': 'December'}
					end_with += f'{mapping[rem["month"]]} {rem["day"]}, '

			# starting on 'YYYY-MM-DD HH:MM' and ending on 'YYYY-MM-DD HH:MM'
			if 'start_time' in rem:
				end_with += f'starting on {rem["start_time"]}, '
			else:
				end_with += 'starting now, '
			if 'end_time' in rem:
				end_with += f'ending on {rem["end_time"]}'
			else:
				end_with += 'never ending'

		confirmation_message = await thread.send(f'{rem["start_with"]}Confirma l\'activació del recordatori:\n{end_with}')
		await confirmation_message.add_reaction('✅')
		await confirmation_message.add_reaction('❌')
		rem['q_message_id'] = confirmation_message.id

	if step == 0 and emoji: # creation message
		if emoji == '❔':
			# send info message
			if await q_info_exists(): return
			q_info = await thread.send(get_q_info_text())
			rem['q_info_id'] = q_info.id
		elif emoji == '✅':
			# pass to next question
			q_message = await thread.send(f'{rem["start_with"]}Vols que el recordatori es repeteixi?')
			await q_message.add_reaction('✅')
			await q_message.add_reaction('❌')
			rem['q_message_id'] = q_message.id
			rem['step'] = 1
			rem['q_info_id'] = 0
		elif emoji == '❌':
			# cancel reminder
			await thread.send(f'{rem["start_with"]}Recordatori cancel·lat.')
			await pop_open_reminder(reminder_id)
			return
		else: return
	elif step == 1 and emoji: # repeat?
		if emoji == '✅':
			# pass to next question
			q_message = await thread.send(f"{rem['start_with']}Especifica l'interval i l'hora.")
			await q_message.add_reaction('❔')
			rem['q_message_id'] = q_message.id
			rem['step'] = 2
		elif emoji == '❌':
			# pass to next question
			q_message = await thread.send(f"{rem['start_with']}Especifica la data i l'hora.")
			await q_message.add_reaction('❔')
			rem['q_message_id'] = q_message.id
			rem['step'] = 5
		else: return
	elif step == 2: # interval & time
		if emoji and emoji == '❔':
			# send info message
			if await q_info_exists(): return
			q_info = await thread.send(get_q_info_text())
			rem['q_info_id'] = q_info.id
		elif user_input:
			params = parse_interval(user_input)
			if not params:
				# if not valid, ask again
				await thread.send(f'{rem["start_with"]}Aquest no és un interval vàlid. Torna-ho a provar.')
				return
			# if valid, set parameters and pass to next question
			for key, value in params.items():
				if value: rem[key] = value
			# if start_date is already set, pass to step 4
			if 'start_date' in rem:
				rem['step'] = 4
				q_message = await thread.send(f"{rem['start_with']}Especifica la data i hora de finalització.")
				await q_message.add_reaction('❔')
				rem['q_message_id'] = q_message.id
			else:
				rem['step'] = 3
				q_message = await thread.send(f"{rem['start_with']}Especifica la data i hora d'inici.")
				await q_message.add_reaction('❔')
				rem['q_message_id'] = q_message.id
		else: return
	elif step == 3: # start date & time
		if emoji and emoji == '❔':
			# send info message
			if await q_info_exists(): return
			q_info = await thread.send(get_q_info_text())
			rem['q_info_id'] = q_info.id
		elif user_input:
			# parse date
			start_date = dateparser.parse(user_input, settings=dateparser_settings)
			if not start_date:
				# if not valid, ask again
				await thread.send(f'{rem["start_with"]}Aquesta no és una data vàlida. Torna-ho a provar. Si no funciona, \
			  					prova aquest format: `YYYY-MM-DD HH:MM:SS`')
				return
			# if valid, set parameters and pass to next question
			rem['start_date'] = start_date.strftime('%Y-%m-%d %H:%M:%S')
			rem['step'] = 4
			q_message = await thread.send(f"{rem['start_with']}Especifica la data i hora de finalització.")
			await q_message.add_reaction('❔')
			rem['q_message_id'] = q_message.id
		else: return
	elif step == 4: # end date & time
		if emoji and emoji == '❔':
			if await q_info_exists(): return
			# get thread and send info message
			q_info = await thread.send(get_q_info_text())
			rem['q_info_id'] = q_info.id
		elif user_input:
			# parse date
			end_date = dateparser.parse(user_input, settings=dateparser_settings)
			if not end_date:
				# if not valid, ask again
				await thread.send(f'{rem["start_with"]}Aquesta no és una data vàlida. Torna-ho a provar. Si no funciona, \
			  					prova aquest format: `YYYY-MM-DD HH:MM:SS`')
				return
			# if valid, set parameters and pass to next question
			rem['end_date'] = end_date.strftime('%Y-%m-%d %H:%M:%S')
			rem['step'] = 6
			await mention_question()
		else: return
	elif step == 5: # date & time
		if emoji and emoji == '❔':
			if await q_info_exists(): return
			# get thread and send info message
			q_info = await thread.send(get_q_info_text())
			rem['q_info_id'] = q_info.id
		elif user_input:
			# parse date
			date = dateparser.parse(user_input, settings=dateparser_settings)
			if not date:
				# if not valid, ask again
				await thread.send(f'{rem["start_with"]}Aquesta no és una data vàlida. Torna-ho a provar. Si no funciona, \
			  					prova aquest format: `YYYY-MM-DD HH:MM:SS`')
				return
			# if valid, set parameters and pass to next question
			rem['trigger'] = 'date'
			rem['run_date'] = date.strftime('%Y-%m-%d %H:%M:%S')
			rem['step'] = 6
			await mention_question()
		else: return
	elif step == 6 and emoji: # mention
		if emoji == ':one:': # author
			author = await bot.fetch_user(rem['author_id'])
			rem['mention'] = author.mention
		elif emoji == ':two:': # everyone
			rem['mention'] = '@everyone'
		elif emoji == ':three:': # here
			rem['mention'] = '@here'
		elif emoji == ':four:': # nobody
			rem['mention'] = ''
		else: return
		await send_confirmation_message()
		rem['step'] = 8
	elif step == 7 and emoji: # mention you?
		if emoji == '✅':
			author = await bot.fetch_user(rem['author_id'])
			rem['mention'] = author.mention
		elif emoji == '❌':
			rem['mention'] = ''
		else: return
		await send_confirmation_message()
		rem['step'] = 8
	elif step == 8 and emoji: # confirmation message
		if emoji == '✅':
			await thread.send(f'{rem["start_with"]}Recordatori activat correctament.')
			await finish_reminder(reminder_id)
			return
		elif emoji == '❌':
			await thread.send(f'{rem["start_with"]}Recordatori cancel·lat.')
			await pop_open_reminder(reminder_id)
			return
		else: return
	else: return
	# remove reminder from list and add it again, updated
	retrieve_item(data['open_reminders'], 'id', reminder_id, remove=True)
	data['open_reminders'].append(rem)
	await write_to_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json', json.dumps(data))

async def finish_reminder(reminder_id):
	# pass it from "open_reminders" to "reminders" list
	f = await read_from_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json')
	data = json.loads(f)
	rem = retrieve_item(data['open_reminders'], 'id', reminder_id, remove=True)
	data['reminders'].append(rem)
	await write_to_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json', json.dumps(data))

async def activate_reminder(scheduler, bot, reminder_id):
	# activate reminder
	rem = await retrieve_reminder_from_file(reminder_id)
	scheduler.add_job(send_reminder, **rem, args=[bot, reminder_id], tags=['reminder'])
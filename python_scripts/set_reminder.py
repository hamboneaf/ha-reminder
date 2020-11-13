#------------------------------------------------------------------------------
# Set / update reminder sensor
#
# Data:
#   name: Sensor name (required)
#   date: Reminder date time D/M/Y-H:M (required, time is optional)
#   title: Reminder title (optional)
#   recurrence: yearly, montly, daily, does not repeat (optional, default 'yearly')
#   every:
#   tag: (optional, default 'reminder')
#   notifier: (optional)
#   script: (optional)
#   message: (optional)
#------------------------------------------------------------------------------

# Reminder name
name = data.get('name').replace(" ", "_")
# Default icon
default_icon = "mdi:calendar-star"
# Days before to notify
days_notice = 0
# Reminder recurrence
recurrence = data.get('recurrence', 'yearly').lower()
# Sensor name derived from name
sensor_name = "sensor.{}".format(name)
# Reminder title (will be sensor friendly_name)
title = data.get('title', 'Reminder')
# Reminder tag
tag = data.get('tag', 'reminder')
# Every (recurrence every)
every = int(data.get('every', 1))
# Reminder action (notify / script)
notifier = data.get('notifier')
script = data.get('script')
# Action message
message = data.get('message', title)
# Split to date and time
date_time = data.get('date').split('T')
# Enabled / disabled
enable = data.get('enable', 'on')

# Default values
new_state = 'off'
remaining_days = 0
friendly_date = "-\-\-"
# next_date = None
# reminder_date = None

# Convert the date
date_split = date_time[0].split("-")
date_day = int(date_split[0])
date_month = int(date_split[1])
date_year =  int(date_split[2])

# Check if time was specified
if len(date_time) == 2:
    all_day = False
    time_split = date_time[1].split(":")
    time_hour = int(time_split[0])
    time_minute = int(time_split[1])
else:
    all_day = True
    time_hour = 0
    time_minute = 0

#
calc_date = datetime.datetime.now().replace(hour=time_hour, minute=time_minute, second=0, microsecond=0)
# End of reminder date time
calc_midnight_date = datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

# Helper function
def datebuild(year, month, day, hour, minute, offset):
    date_str = "{}-{}-{} {}:{}".format(
        str(year),
        str(month),
        str(day),
        str(hour),
        str(minute),
    )
    return datetime.datetime.strptime(
        date_str, "%Y-%m-%d %H:%M"
    ) + datetime.timedelta(-offset)

# Helper function
def dateadd(t1, n, type):
    if type == 'years':
        t = t1.replace(t1.year + n)
    elif type == 'months':
        t = t1
        while n > 0:
            month = t.month + 1
            year = t.year
            if month > 12:
                month = 1
                year = year + 1
            t = t.replace(year=year, month=month)
            n = n - 1
    elif type == 'days':
        t = t1 + datetime.timedelta(days=n)
    elif type == 'weeks':
        t = t1 + datetime.timedelta(days=7*n)
    return t

# Helper function
def datediff(t1, t2, type):
    diff = 0
    if t1 > t2:
        t1, t2 = t2, t1
    if type == 'months':
        while t1 < t2:
            month = t1.month + 1
            year = t1.year
            if month > 12:
                month = 1
                year = year + 1
            t1 = t1.replace(year=year, month=month)
            diff = diff + 1
        diff = diff - 1
    elif type == 'weeks':
        diff = int((t2 - t1).days / 7)
    elif type == 'years':
        diff = t2.year - t1.year
    elif type == 'days':
        diff = (t2 - t1).days
    return diff

# Helper function
def datenext(t1, t2, n, type):
    if t1 < t2:
        diff = datediff(t1, t2, type)
        return dateadd(t1, n * int(((diff + n) / n)), type)
    return t1

# Reminder date and next reminder date
if recurrence == 'yearly':
    reminder_date = datebuild(
        calc_date.year,
        date_month, date_day, time_hour, time_minute, days_notice
    )
    # Next occurrence date
    next_date = datenext(reminder_date, calc_date, every, 'years')
elif recurrence == 'monthly':
    reminder_date = datebuild(
        calc_date.year, calc_date.month,
        date_day, time_hour, time_minute, days_notice
    )
    # Next occurrence date
    next_date = datenext(reminder_date, calc_date, every, 'months')
elif recurrence == 'weekly':
    logger.error('Not implemented yet 2')
elif recurrence == 'daily':
    reminder_date = datebuild(
        calc_date.year, calc_date.month, calc_date.day,
        time_hour, time_minute, days_notice
    )
    # Next occurrence date
    next_date = datenext(reminder_date, calc_date, every, 'days')
elif recurrence == 'does not repeat':
    reminder_date = datebuild(
        date_year, date_month, date_day, time_hour, time_minute, days_notice
    )
    next_date = None

# sensor current state
current_state = hass.states.get(sensor_name).state

# Sensor new state
if calc_date <= reminder_date <= calc_midnight_date:
    new_state = 'on'

# Remaining days to next occurence
if next_date and new_state == 'off':
    remaining_days = (next_date - calc_date).days

# Format friendly next reminder date
if next_date:
    logger.debug(next_date)
    if all_day:
        friendly_date = "{:04d}-{:02d}-{:02d}".format(
            next_date.year, next_date.month, next_date.day)
    else:
        friendly_date = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}".format(
            next_date.year, next_date.month, next_date.day, next_date.hour, next_date.minute)

# Send the sensor to homeassistant
hass.states.set(sensor_name , new_state,
    {
        "icon" : data.get("icon", default_icon),
        "friendly_name" : "{}".format(title),
        "friendly_date": friendly_date,
        "remaining": remaining_days,
        "recurrence": recurrence,
        "every": every,
        "enable": enable,
        "tag": tag
    }
)

# Actions
if new_state == 'on' and current_state == 'off':
    if notifier:
        hass.services.call('notify', notifier,
            {
                "title": "Reminder",
                "message": message
            }
        )
    if script:
        hass.services.call('script', script,
            {
                "message": message
            }
        )

# For debugging
logger.debug("Reminder current:{} new:{} reminder:{} next:{} calc:{} midnight:{}".format(
    current_state, new_state, reminder_date, next_date, calc_date, calc_midnight_date)
    )

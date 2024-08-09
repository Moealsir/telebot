import asyncio
import datetime
import os
import json
from telethon import TelegramClient, events, Button

API_ID = '20538654'
API_HASH = '9ba174bab918c17cfba4c4619f2e0ac6'
BOT_TOKEN = '6848793992:AAG75oXKooJONjnVox8PZr_tLVuPLZZk7-Q'

client = TelegramClient('bot', API_ID, API_HASH)

# Files
LIMITS_FILE = 'user_limits.json'
KEYS_FILE = 'keys.txt'
STATS_FILE = 'stats.json'
AUTHORIZED_FILE = 'authorized.json'
ADMINS_FILE = 'admins.json'
TRC20_WALLET = 'TAvV8bJLFHhSpKJ3ZYDLStwV92Lh9jzcgv'
BNB_WALLET = '0x0a7457aA8C9f26f2CCA68A7aCEf66175eA93e0a7'

# Initialize global variables
user_limits = {}
stats = {}
authorized_users = set()
admin_users = set()

def load_user_limits():
    global user_limits
    if os.path.exists(LIMITS_FILE):
        with open(LIMITS_FILE, 'r') as f:
            user_limits = json.load(f)
    else:
        user_limits = {}

def save_user_limits():
    with open(LIMITS_FILE, 'w') as f:
        json.dump(user_limits, f)

def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)
    else:
        stats = {'keys_used': 0, 'user_count': 0, 'remaining_keys': {'bike': 0, 'clone': 0, 'cube': 0, 'train': 0}}

def save_stats():
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

def load_authorized_users():
    global authorized_users
    if os.path.exists(AUTHORIZED_FILE):
        with open(AUTHORIZED_FILE, 'r') as f:
            raw_authorized_users = json.load(f)
            # Normalize user identifiers
            authorized_users = set()
            for user in raw_authorized_users:
                user = user.lstrip('@')  # Remove '@' if present
                authorized_users.add(user)
    else:
        authorized_users = set()

def load_admin_users():
    global admin_users
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, 'r') as f:
                raw_admin_users = json.load(f)
                # Normalize admin usernames
                admin_users = set()
                for user in raw_admin_users:
                    print(user)
                    admin_users.add(user.lstrip('@'))  # Remove '@' if present
        except json.JSONDecodeError:
            print(f"Error reading {ADMINS_FILE}, resetting to empty.")
            admin_users = set()
    else:
        admin_users = set()

def save_authorized_users():
    with open(AUTHORIZED_FILE, 'w') as f:
        json.dump(list(authorized_users), f)

def save_admin_users():
    with open(ADMINS_FILE, 'w') as f:
        json.dump(list(admin_users), f)

def is_user_authorized(event):
    user_id = str(event.sender_id)
    username = event.sender.username or ''
    normalized_username = username.lstrip('@')
    return user_id in authorized_users or normalized_username in authorized_users

def is_admin(event):
    user_id = str(event.sender_id)
    print(f'userid {user_id}')
    username = event.sender.username or ''
    print(f'username {username}')
    normalized_username = username.lstrip('@')
    
    # Check if the user is an admin based on user_id or normalized username
    return user_id in admin_users or normalized_username in admin_users

def reset_user_limits():
    global user_limits
    user_limits = {}
    save_user_limits()

def update_stats(key_type):
    global stats
    if key_type in stats['remaining_keys']:
        stats['remaining_keys'][key_type] -= 1
        stats['keys_used'] += 1
    save_stats()

def get_key_from_file(key_type):
    try:
        with open(KEYS_FILE, 'r') as f:
            keys = f.readlines()

        for index, key in enumerate(keys):
            if key_type.upper() in key:
                with open(KEYS_FILE, 'w') as f:
                    f.writelines(keys[:index] + keys[index + 1:])
                update_stats(key_type)
                return key.strip()
    except Exception as e:
        print(f"Error while reading keys: {e}")
    return None

async def handle_request(event, key_type):
    user_id = event.sender_id
    current_date = str(datetime.date.today())
    print(f"Handling request for {user_id} for key type {key_type}")

    # Initialize user's daily data
    if user_id not in user_limits:
        user_limits[user_id] = {'date': current_date, 'counts': {'bike': 0, 'clone': 0, 'cube': 0, 'train': 0}}

    user_data = user_limits[user_id]

    # Reset the user's count if it's a new day
    if user_data['date'] != current_date:
        user_data['date'] = current_date
        user_data['counts'] = {'bike': 0, 'clone': 0, 'cube': 0, 'train': 0}

    # Determine the limit based on authorization
    limit = 4 if is_user_authorized(event) else 2

    # Check if the user has exceeded the limit
    if user_data['counts'][key_type] >= limit:
        await event.respond("You have reached your limit for today. Try again tomorrow.")
        return

    # Provide the requested key
    key = get_key_from_file(key_type)
    if key:
        user_data['counts'][key_type] += 1
        save_user_limits()
        await event.respond(f"Here is your {key_type} key: `{key}`")
    else:
        await event.respond("No keys available at the moment.")

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    current_date = str(datetime.date.today())

    # Initialize user's daily data
    if user_id not in user_limits:
        user_limits[user_id] = {'date': current_date, 'counts': {'bike': 0, 'clone': 0, 'cube': 0, 'train': 0}}
        stats['user_count'] += 1
        save_stats()

    user_data = user_limits[user_id]

    # Reset the user's count if it's a new day
    if user_data['date'] != current_date:
        user_data['date'] = current_date
        user_data['counts'] = {'bike': 0, 'clone': 0, 'cube': 0, 'train': 0}

    # Prepare limits message
    limit = 4 if is_user_authorized(event) else 2
    limits_message = '\n'.join(
        [f"{key.capitalize()}: {limit - count} remaining" for key, count in user_data['counts'].items()]
    )

    buttons = [
        [Button.text('Bike 🚲'), Button.text('Clone 🔃')],
        [Button.text('Cube 🟧'), Button.text('Train 🚂')],
        [Button.text('Stats 📊'), Button.text('Buy More 💲')],
        [Button.text('Donate 💸')]
    ]

    if is_admin(event):
        buttons.append([Button.text('Settings ⚙️')])

    await event.respond(f'Choose an option:\n{limits_message}', buttons=buttons)

@client.on(events.NewMessage)
async def handle_incoming_message(event):
    user_id = event.sender_id
    text = event.raw_text
    print(f"Received message: {text}")

    if text == 'Bike 🚲':
        await handle_request(event, 'bike')
    elif text == 'Clone 🔃':
        await handle_request(event, 'clone')
    elif text == 'Cube 🟧':
        await handle_request(event, 'cube')
    elif text == 'Train 🚂':
        await handle_request(event, 'train')
    elif text == 'Stats 📊':
        try:
            with open(KEYS_FILE, 'r') as f:
                keys = f.readlines()
            counts = {
                'bike': sum(1 for key in keys if 'BIKE' in key),
                'clone': sum(1 for key in keys if 'CLONE' in key),
                'cube': sum(1 for key in keys if 'CUBE' in key),
                'train': sum(1 for key in keys if 'TRAIN' in key)
            }
            remaining_keys_message = '\n'.join([f"{key.capitalize()}: {count}" for key, count in counts.items()])
            stats_message = (
                f"Keys used: {stats['keys_used']}\n"
                f"Users: {stats['user_count']}\n"
                f"Keys left:\n{remaining_keys_message}"
            )
            await event.respond(f"Stats:\n{stats_message}")
        except Exception as e:
            print(f"Error retrieving stats: {e}")
            await event.respond("Error retrieving stats.")
    elif text == 'Buy More 💲':
        await event.respond("You can buy more keys from our website.")
    elif text == 'Donate 💸':
        await event.respond(f"Thank you for considering a donation! Here is my Wallets \n\nTRC20: `{TRC20_WALLET}`\n\n BNB: `{BNB_WALLET}` \n\n Contact Develeper @Moealsir")
    elif text == 'command':
        if is_admin(event):
            await event.respond(f'here are the adding command: ')
        else:
            await event.respond("You are not authorized to use this command.")
    elif text.startswith('add authorized '):
        if is_admin(event):
            user_to_add = text[17:].lstrip('@')  # Remove 'add authorized ' and '@' if present
            if user_to_add:
                authorized_users.add(user_to_add)
                save_authorized_users()
                await event.respond(f"User `{user_to_add}` has been added to the authorized list.")
            else:
                await event.respond("Please provide a valid user ID or username.")
        else:
            await event.respond("You are not authorized to use this command.")
    elif text.startswith('edit authorized '):
        if is_admin(event):
            user_id = text[17:].lstrip('@')  # Remove 'edit authorized ' and '@' if present
            if user_id:
                authorized_users.add(user_id)
                save_authorized_users()
                await event.respond(f"User `{user_id}` has been added to the authorized list.")
            else:
                await event.respond("Please provide a valid user ID or username.")
        else:
            await event.respond("You are not authorized to use this command.")
    elif text.startswith('remove authorized '):
        if is_admin(event):
            user_to_remove = text[19:].lstrip('@')  # Remove 'remove authorized ' and '@' if present
            if user_to_remove in authorized_users:
                authorized_users.remove(user_to_remove)
                save_authorized_users()
                await event.respond(f"User `{user_to_remove}` has been removed from the authorized list.")
            else:
                await event.respond("User not found in the authorized list.")
        else:
            await event.respond("You are not authorized to use this command.")
    elif text.startswith('add admin '):
        if is_admin(event):
            user_to_add = text[10:].lstrip('@')  # Remove 'add admin ' and '@' if present
            if user_to_add:
                admin_users.add(user_to_add)
                save_admin_users()
                await event.respond(f"User `{user_to_add}` has been added to the admin list.")
            else:
                await event.respond("Please provide a valid user ID or username.")
        else:
            await event.respond("You are not authorized to use this command.")
    elif text.startswith('edit admin '):
        if is_admin(event):
            user_id = text[11:].lstrip('@')  # Remove 'edit admin ' and '@' if present
            if user_id:
                admin_users.add(user_id)
                save_admin_users()
                await event.respond(f"User `{user_id}` has been added to the admin list.")
            else:
                await event.respond("Please provide a valid user ID or username.")
        else:
            await event.respond("You are not authorized to use this command.")
    elif text.startswith('remove admin '):
        if is_admin(event):
            user_to_remove = text[13:].lstrip('@')  # Remove 'remove admin ' and '@' if present
            if user_to_remove in admin_users:
                admin_users.remove(user_to_remove)
                save_admin_users()
                await event.respond(f"User `{user_to_remove}` has been removed from the admin list.")
            else:
                await event.respond("User not found in the admin list.")
        else:
            await event.respond("You are not authorized to use this command.")

async def reset_limits_daily():
    while True:
        now = datetime.datetime.now()
        next_reset = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min)
        delay = (next_reset - now).total_seconds()
        print(f"Waiting for {delay} seconds until the next reset")
        await asyncio.sleep(delay)
        reset_user_limits()
        print("User limits have been reset.")

async def main():
    load_user_limits()
    load_stats()
    load_authorized_users()
    load_admin_users()
    asyncio.create_task(reset_limits_daily())
    await client.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())


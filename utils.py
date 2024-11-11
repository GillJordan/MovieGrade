import logging
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from info import *
from imdb import Cinemagoer
import asyncio
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram import enums
from typing import Union
import subprocess
import re
import os
from datetime import datetime
from typing import List
from database.users_chats_db import db
from bs4 import BeautifulSoup
import requests
import aiohttp
from pymongo import MongoClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)

imdb = Cinemagoer()

BANNED = {}
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

# temp db for banned 
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CURRENT=int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    
async def is_subscribed(bot, query):
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        pass
    except Exception as e:
        logger.exception(e)
    else:
        if user.status != 'kicked':
            return True

    return False

async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        # https://t.me/GetTGLink/4183
        query = (query.strip()).lower()
        title = query
        year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1]) 
        else:
            year = None
        movieid = imdb.search_movie(title.lower(), results=10)
        if not movieid:
            return None
        if year:
            filtered=list(filter(lambda k: str(k.get('year')) == str(year), movieid))
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid
        movieid=list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
        if not movieid:
            movieid = filtered
        if bulk:
            return movieid
        movieid = movieid[0].movieID
    else:
        movieid = query
    movie = imdb.get_movie(movieid)
    if movie.get("original air date"):
        date = movie["original air date"]
    elif movie.get("year"):
        date = movie.get("year")
    else:
        date = "N/A"
    plot = ""
    if not LONG_IMDB_DESCRIPTION:
        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
    else:
        plot = movie.get('plot outline')
    if plot and len(plot) > 800:
        plot = plot[0:800] + "..."

    return {
        'title': movie.get('title'),
        'votes': movie.get('votes'),
        "aka": list_to_str(movie.get("akas")),
        "seasons": movie.get("number of seasons"),
        "box_office": movie.get('box office'),
        'localized_title': movie.get('localized title'),
        'kind': movie.get("kind"),
        "imdb_id": f"tt{movie.get('imdbID')}",
        "cast": list_to_str(movie.get("cast")),
        "runtime": list_to_str(movie.get("runtimes")),
        "countries": list_to_str(movie.get("countries")),
        "certificates": list_to_str(movie.get("certificates")),
        "languages": list_to_str(movie.get("languages")),
        "director": list_to_str(movie.get("director")),
        "writer":list_to_str(movie.get("writer")),
        "producer":list_to_str(movie.get("producer")),
        "composer":list_to_str(movie.get("composer")) ,
        "cinematographer":list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_str(movie.get("genres")),
        'poster': movie.get('full-size cover url'),
        'plot': plot,
        'rating': str(movie.get("rating")),
        'url':f'https://www.imdb.com/title/tt{movieid}'
    }
# https://github.com/odysseusmax/animated-lamp/blob/2ef4730eb2b5f0596ed6d03e7b05243d93e3415b/bot/utils/broadcast.py#L37

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
        }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.content.decode(), 'lxml')
    
    # Added
    titles = soup.find_all('h3')
    search_results = [title.getText() for title in titles]
    return search_results



async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)
    
def get_size(size):
    """Get size in readable format"""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]  

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    """extracts the user from a message"""
    # https://github.com/SpEcHiDe/PyroGramBot/blob/f30e2cca12002121bad1982f68cd0ff9814ce027/pyrobot/helper_functions/extract_user.py#L7
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
           
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time


def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1  # ignore first char -> is some kind of quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)

    # 1 to avoid starting quote, and counter is exclusive so avoids ending
    key = remove_escapes(text[1:counter].strip())
    # index will be in range, or `else` would have been executed and returned
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res


def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


async def toggle_earn_status(database, status=None):
    try:
        col = database['statusSettings']
        doc = col.find_one({'name':'earn_status'})
        if doc:
            if not status:
                if doc['value'] == 'true':
                    status = False
                else:
                    status = True

            col.update_one(doc, {'$set':{'value':str(status).lower()}})
            print('Your earn status is', 'on' if status else 'off')
            return status
        else:
            col.insert_one({
                'name':'earn_status',
                'value':'true' if status else 'false'
            })
            print('Your earn status is', 'on 'if status else 'off')
            return True if status else False


    except Exception as e:
        logger.error(e)


async def get_earn_status(database):
    try:
        col = database['statusSettings']
        doc = col.find_one({'name':'earn_status'})
        if doc and doc['value'] == 'true':
            return True

    except Exception as e:
        logger.error(e)
    
    return False


async def get_shortlink(link, end_point, api_key):
    if end_point and api_key:

        scheme = link.split(":")[0]
        if scheme == 'http':
            link = link.replace("http", 'https')

        # alias = end_point.find('&alias')
        # if alias != -1:
        #     end_point = end_point[:alias]

        url = end_point.format(api_key, link)

        try:
            async with aiohttp.ClientSession() as session:
                print(url)
                async with session.get(url, raise_for_status=True, ssl=False) as response:
                    if response.status == 200:
                        print(response.content_type)
                        if response.content_type == 'application/json':
                            data = await response.json()
                            print(data)
                            if data["status"] == "success":
                                return data['shortenedUrl']

                        elif response.content_type == 'text/html':
                            data = await response.read()
                            data = data.decode()

                            if 'https://' or 'http://' in data:
                                return data
                        else:
                            logger.error(f"Error: {response}")

        except Exception as e:
            logger.error(e)

    elif not (end_point or api_key):
        logger.warning('Missing end_point and api_key')
    
    return link


async def get_invite_link(client):
    
    col = client.database['statusSettings']
    doc = col.find_one({'name':'invite_link'})

    if doc:
        return doc['value']

    else:
        invite_link = await client.create_chat_invite_link(
            DELIVERY_CHANNEL,
            'Customized_Eva_Maria'
        )
        invite_link = invite_link.invite_link

        col.insert_one({
            'name': 'invite_link',
            'value': invite_link
        })

    return invite_link


async def set_shortener(db, id, url):
    try:
        col = db['downUsers']
        col.find_one_and_update(
            {'_id':id},
            {'$set':{'shortener':url}},
            upsert=True
        )
        return True
    except Exception as e:
        print(e)


async def set_api(db, id, key):
    try:
        col = db['downUsers']
        col.find_one_and_update(
            {'_id':id},
            {'$set':{'api_key':key}},
            upsert=True
        )
        return True
    except Exception as e:
        print(e)


async def add_group(db, user_id, group_id):
    try:
        col = db['downGroups']
        res = col.insert_one(
            {
                '_id': group_id,
                'user_id': user_id
            }
        )
        print(res)
    except Exception as e:
        print('Failed to enroll group')
        print(e)


async def remove_group(db, group_id):
    try:
        col = db['downGroups']
        col.find_one_and_delete(
            {
                '_id': group_id,
            }
        )
    except Exception as e:
        print(e) 


async def list_groups(db, user_id):
    try:
        col = db['downGroups']
        groups = col.find(
            {
                'user_id': user_id
            }
        )
        if groups:
            return [group['_id'] for group in groups]

    except Exception as e:
        print(e)


async def get_down_user(db, group_id):
    try:
        col = db['downGroups']
        group = col.find_one(
            {
                '_id': group_id
            }
        )
        if group:
            return group['user_id']

    except Exception as e:
        print(e)


async def get_user_creds(db, user_id):
    try:
        col = db['downUsers']
        user = col.find_one(
            {
                '_id': user_id
            }
        )
        if user:
            return user['shortener'], user['api_key']

    except Exception as e:
        print(e)


async def toggle_convert_status(database, status=None):
    try:
        col = database['statusSettings']
        doc = col.find_one({'name':'convert_status'})
        if doc:
            if not status:
                if doc['value'] == 'true':
                    status = False
                else:
                    status = True

            col.update_one(doc, {'$set':{'value':str(status).lower()}})
            print('Your convert status is', 'on' if status else 'off')
            return status
        else:
            col.insert_one({
                'name':'convert_status',
                'value':'true' if status else 'false'
            })
            print('Your convert status is', 'on' if status else 'off')
            return True if status else False


    except Exception as e:
        logger.error(e)


async def get_convert_status(database):
    try:
        col = database['statusSettings']
        doc = col.find_one({'name':'convert_status'})
        if doc and doc['value'] == 'true':
            return True

    except Exception as e:
        logger.error(e)
    
    return False


async def get_duration(file):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return float(result.stdout)


async def delete_user(db, user_id):
    try:
        col = db['downUsers']
        col.find_one_and_delete(
            {
                '_id': user_id
            }
        )
        return True

    except Exception as e:
        print(e)


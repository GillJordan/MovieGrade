import asyncio
import re
import os
import ast
import math
import time
from random import randint
from utils import get_shortlink, toggle_earn_status, get_earn_status, set_shortener, set_api, remove_group, list_groups, get_down_user, get_user_creds, toggle_convert_status, get_duration, get_invite_link, delete_user
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import *
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, temp, get_settings, save_group_settings, search_gagala
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
from pyrogram.enums.chat_type import ChatType
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
import logging
from shorteners import supported_shorteners

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}
FILTER_MODE = {}

prev_edit = 0

# Added
@Client.on_message(filters.left_chat_member & filters.group)
async def left_chat(client, message):
    await remove_group(client.database, message.chat.id)


@Client.on_message(filters.private & filters.command(['quit']))
async def delete_down_user(bot, message):
    if message.chat.id not in ADMINS:
        res = await delete_user(bot.database, message.chat.id)
        if res:
            return await message.reply(
                'Your account has beed deleted successfully. You can Join back anytime.'
            )
    return await message.reply(
        'Something went wrong. Try again later'
    )


@Client.on_message(filters.private & filters.command(['convert']))
async def toggle_convert(bot, message):

    if message.chat.id in ADMINS:
        new_status = await toggle_convert_status(bot.database)

        if new_status != None:
            return await message.reply(
                f"Now users will {'' if new_status else 'not '}be given option to convert files between document and video."
            )

        return await message.reply(
            'Failed to change convert status :('
        )
    return await message.reply(
        'You are not authorized to use this command'
    )



@Client.on_message(filters.private & filters.command(['short']))
async def toggle_earn(bot, message):

    if message.chat.id in ADMINS:
        new_status = await toggle_earn_status(bot.database)

        if new_status != None:
            return await message.reply(
                f"Now links will {'' if new_status else 'not '}be shorted before providing to user."
            )

        return await message.reply(
            'Failed to change short status :('
        )
    return await message.reply(
        'You are not authorized to use this command'
    )


@Client.on_message(filters.private & filters.command(['groups']))
async def show_groups(client, message):
    if message.chat.id not in ADMINS:
        group_ids = await list_groups(client.database, message.chat.id)
        if group_ids:
            group_names = []
            for count, group_id in enumerate(group_ids):
                group = await client.get_chat(group_id)
                group_names.append(
                    f'{count + 1}. {group.title} - ({group.members_count})'
                )
            await message.reply('\n'.join(group_names))

        else:
            await message.reply('You have not added me in any group yet')
    else:
        await message.reply('This feature is not for admins')


@Client.on_message(filters.private & filters.command(['shortener']))
async def shortener(client, message):
    if message.chat.id not in ADMINS:
        _, *args = message.text.split()
        if args:
            api_url = args[0]
            res = await set_shortener(client.database, message.from_user.id, api_url)
            if res:
                return await message.reply('Shortener setup **successful**')

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton('HOW TO SET SHORTENER ?', callback_data='how_to_set_shortener')]
        ])
        
        await message.reply(
            'Failed to set **shortener**. Click on the below button to learn more.',
            reply_markup=reply_markup
        )
    else:
        await message.reply('This feature is not for admins')


@Client.on_message(filters.private & filters.command(['api']))
async def api(client, message):
    if message.chat.id not in ADMINS:
        _, *args = message.text.split()
        if args:
            api_key = args[0]
            if api_key.isalnum():
                res = await set_api(client.database, message.from_user.id, api_key)
                if res:
                    return await message.reply('Successfully set **API Token**')
            else:
                return await message.reply(
                "The **API Token** you trying to set is invalid. Please visit your **Url Shortener**'s website and copy your valid **API Token**",
            )
        
        await message.reply(
            'Failed to set **api key**. Please try again later. If it continues to happen, Kindly contact us **[here](https://t.me/crebuo)**',
        )
    else:
        await message.reply('This feature is only for admins')


@Client.on_message(filters.command('autofilter'))
async def fil_mod(client, message): 
      mode_on = ["yes", "on", "true"]
      mode_of = ["no", "off", "false"]

      try: 
         args = message.text.split(None, 1)[1].lower() 
      except: 
         return await message.reply("**𝙸𝙽𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝙲𝙾𝙼𝙼𝙰𝙽𝙳...**")
      
      m = await message.reply("**𝚂𝙴𝚃𝚃𝙸𝙽𝙶.../**")

      if args in mode_on:
          FILTER_MODE[str(message.chat.id)] = "True" 
          await m.edit("**𝙰𝚄𝚃𝙾𝙵𝙸𝙻𝚃𝙴𝚁 𝙴𝙽𝙰𝙱𝙻𝙴𝙳**")
      
      elif args in mode_of:
          FILTER_MODE[str(message.chat.id)] = "False"
          await m.edit("**𝙰𝚄𝚃𝙾𝙵𝙸𝙻𝚃𝙴𝚁 𝙳𝙸𝚂𝙰𝙱𝙻𝙴𝙳**")
      else:
          await m.edit("USE :- /autofilter on 𝙾𝚁 /autofilter off")


# use (filters.group | filters.private) &... to enable pm requests

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    k = await manual_filters(client, message)
    if k == False:
        await auto_filter(client, message)


@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer("oKda", show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer("You are using one of my old messages, please send the request again.", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)

    #Added 
    end_point, api_key = '', ''

    if query.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        down_user = await get_down_user(bot.database, query.message.chat.id)

        if down_user:
            user_cred = await get_user_creds(bot.database, down_user)

            if user_cred:
                shortener, api_key = user_cred
                print(shortener)
                end_point = supported_shorteners[shortener]['api_url']
                print(end_point)

    if not (end_point and api_key):
        short = await get_earn_status(bot.database)

        if short:
            end_point, api_key = URL_SHORTENER_END_POINT, URL_SHORTENER_API_KEY

    print(end_point, api_key)

    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}", 
                    url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file.file_unique_id}", end_point, api_key)
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}", 
                    url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file.file_unique_id}", end_point, api_key)
                ),
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}", 
                    url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file.file_unique_id}", end_point, api_key)
                ),
            ]
            for file in files
        ]

    btn.insert(0,
        [
            InlineKeyboardButton(text="⚡ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ⚡", url='https://t.me/MovieGrade')
        ]
    )

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⏪ 𝗕𝗮𝗰𝗸", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"📃 𝗣𝗮𝗴𝗲s {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}",
                                  callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"🗓 {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
             InlineKeyboardButton("𝗡𝗲𝘅𝘁 ➡️", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⏪ 𝗕𝗮𝗰𝗸", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"🗓 {math.ceil(int(offset) / 10) + 1} / {math.ceil(total / 10)}", callback_data="pages"),
                InlineKeyboardButton("𝗡𝗲𝘅𝘁 ➡️", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    # await query.answer()


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("😁 𝗛𝗲𝘆 𝗙𝗿𝗶𝗲𝗻𝗱,𝗣𝗹𝗲𝗮𝘀𝗲 𝗦𝗲𝗮𝗿𝗰𝗵 𝗬𝗼𝘂𝗿𝘀𝗲𝗹𝗳.", show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer("𝐋𝐢𝐧𝐤 𝐄𝐱𝐩𝐢𝐫𝐞𝐝 𝐊𝐢𝐧𝐝𝐥𝐲 𝐏𝐥𝐞𝐚𝐬𝐞 𝐒𝐞𝐚𝐫𝐜𝐡 𝐀𝐠𝐚𝐢𝐧 🙂.", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('𝙲𝙷𝙴𝙲𝙺𝙸𝙽𝙶 𝙵𝙸𝙻𝙴 𝙾𝙽 𝙼𝚈 𝙳𝙰𝚃𝙰𝙱𝙰𝚂𝙴...//')
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await query.message.edit('𝚃𝙷𝙸𝚂 𝙼𝙾𝚅𝙸𝙴 I𝚂 𝙽𝙾𝚃 𝚈𝙴𝚃 𝚁𝙴𝙻𝙴𝙰𝚂𝙴𝙳 𝙾𝚁 𝙰𝙳𝙳𝙴𝙳 𝚃𝙾 𝙳𝙰𝚃𝚂𝙱𝙰𝚂𝙴 💌')
            await asyncio.sleep(10)
            await k.delete()

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('Piracy Is Crime')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Buddy Don't Touch Others Property 😁", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "𝙲𝙾𝙽𝙽𝙴𝙲𝚃"
            cb = "connectcb"
        else:
            stat = "𝙳𝙸𝚂𝙲𝙾𝙽𝙽𝙴𝙲𝚃"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("𝙳𝙴𝙻𝙴𝚃𝙴", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("𝙱𝙰𝙲𝙺", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"𝙶𝚁𝙾𝚄𝙿 𝙽𝙰𝙼𝙴 :- **{title}**\n𝙶𝚁𝙾𝚄𝙿 𝙸𝙳 :- `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return await query.answer('Piracy Is Crime')
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"𝙲𝙾𝙽𝙽𝙴𝙲𝚃𝙴𝙳 𝚃𝙾 **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode=enums.ParseMode.MARKDOWN)
        return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"𝙳𝙸𝚂𝙲𝙾𝙽𝙽𝙴𝙲𝚃 FROM **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://telegram.dog/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm']:
                await query.answer(url=f"https://telegram.dog/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False 
                )
                await query.answer('Check PM, I have sent files in pm', show_alert=True)
        except UserIsBlocked:
            await query.answer('You Are Blocked to use me !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.dog/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://telegram.dog/{temp.U_NAME}?start={ident}_{file_id}")
    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("I Like Your Smartness, But Don't Be Oversmart Okay 😒", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False
        )
    elif query.data == "pages":
        await query.answer()
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('⚚ Add Me To Your Group ⚚', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ], [
            InlineKeyboardButton('⚡SubScribe⚡', url='https://youtube.com/@gillharyana'),
            InlineKeyboardButton('🤖 Updates 🤖', url='https://t.me/Ecommerce_Shop')
        ], [
            InlineKeyboardButton('♻️ Help ♻️', callback_data='help'),
            InlineKeyboardButton('♻️ About ♻️', callback_data='about')
        ], [
            InlineKeyboardButton(text='🤑START EARNING🤑',callback_data='start_earning')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        return await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('𝙼𝙰𝙽𝚄𝙴𝙻 𝙵𝙸𝙻𝚃𝙴𝚁', callback_data='manuelfilter'),
            InlineKeyboardButton('𝙰𝚄𝚃𝙾 𝙵𝙸𝙻𝚃𝙴𝚁', callback_data='autofilter')
        ], [
            InlineKeyboardButton('𝙲𝙾𝙽𝙽𝙴𝙲𝚃𝙸𝙾𝙽𝚂', callback_data='coct'),
            InlineKeyboardButton('𝙴𝚇𝚃𝚁𝙰 𝙼𝙾D𝚂', callback_data='extra')
        ], [
            InlineKeyboardButton('🏠 H𝙾𝙼𝙴 🏠', callback_data='start'),
        ], [
            InlineKeyboardButton(text='🤑START EARNING🤑',callback_data='start_earning')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('🏠 H𝙾𝙼𝙴 🏠', callback_data='start'),
         ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='help'),
            InlineKeyboardButton('⏹️ 𝙱𝚄𝚃𝚃𝙾𝙽𝚂', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MANUELFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='manuelfilter')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "extra":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='help'),
            InlineKeyboardButton('👮‍♂️ 𝙰𝙳𝙼𝙸𝙽', callback_data='admin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='extra')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='help'),
            InlineKeyboardButton('♻️ 𝚁𝙴𝙵𝚁𝙴𝚂𝙷', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('👩‍🦯 𝙱𝙰𝙲𝙺', callback_data='help'),
            InlineKeyboardButton('♻️ 𝚁𝙴𝙵𝚁𝙴𝚂𝙷', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('𝐅𝐈𝐋𝐓𝐄𝐑 𝐁𝐔𝐓𝐓𝐎𝐍',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('𝐒𝐈𝐍𝐆𝐋𝐄' if settings["button"] else '𝐃𝐎𝐔𝐁𝐋𝐄',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('𝐁𝐎𝐓 𝐏𝐌', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ 𝐘𝐄𝐒' if settings["botpm"] else '❌ 𝐍𝐎',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('𝐅𝐈𝐋𝐄 𝐒𝐄𝐂𝐔𝐑𝐄',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ 𝐘𝐄𝐒' if settings["file_secure"] else '❌ 𝐍𝐎',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('𝐈𝐌𝐃𝐁', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ 𝐘𝐄𝐒' if settings["imdb"] else '❌ 𝐍𝐎',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('𝐒𝐏𝐄𝐋𝐋 𝐂𝐇𝐄𝐂𝐊',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ 𝐘𝐄𝐒' if settings["spell_check"] else '❌ 𝐍𝐎',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('𝐖𝐄𝐋𝐂𝐎𝐌𝐄', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ 𝐘𝐄𝐒' if settings["welcome"] else '❌ 𝐍𝐎',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    
    elif query.data == "start_earning" and query.message.chat.type == ChatType.PRIVATE:

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton('SELECT SHORTENER', callback_data='select_shortener')],
            [InlineKeyboardButton('BACK', callback_data='start')]
        ])
        return await query.message.edit_text(
            text=(
                f'Hi **{query.from_user.first_name}**, You can also earn using this bot. '
                'Just select your favourite **URL Shortener** and register your **API Token**.\n\n'
                'Then **Add** me into any **Group** as **Admin** and I will provide movies through your shortened links. '
                "You don't have to upload any movie I will manage the rest."
            ),
            reply_markup=reply_markup
        )

    elif query.data in ("select_shortener", "change_shortener") and query.message.chat.type == ChatType.PRIVATE:

        if query.data != 'change_shortener':

            creds = await get_user_creds(client.database, query.message.chat.id)

            if creds:

                selected_shortener, api_key = creds

                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton('ADD ME TO GROUP', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                        ],
                        [
                            InlineKeyboardButton('CHANGE SHORTENER', callback_data='change_shortener')
                        ]
                    ]
                )

                reply_text = (
                    f'Hey **{query.from_user.first_name}**, You have already selected **{selected_shortener}** '
                    f'as your default **URL Shortener** for this account. Your current **API Token** is <pre>{api_key}</pre>\n\n'
                    'Now you can just add me into any of your **Group** and start earning. If you wish to change '
                    'your **URL Shortener** or **API Token**, click on the below button.'
                )

                return await query.message.edit_text(
                    text=reply_text,
                    reply_markup=reply_markup
                )

        reply_markup = InlineKeyboardMarkup(
            [   
                [InlineKeyboardButton(shortener.title(), callback_data=f'selected_{shortener}')]
                for shortener in supported_shorteners
            ] + [
                [InlineKeyboardButton('BACK', callback_data='start_earning')]
            ]
        )
        reply_text = (
            'These are the **URL Shorteners** we currently support. '
            "If you didn't find your favourite **URL Shortener**, You can contact us **[here](https://t.me/crebuo).** "
            "It will be added within an hour."
        )
        return await query.message.edit_text(
            text=reply_text,
            reply_markup=reply_markup
        )
    

    elif query.data.startswith('selected_') and query.message.chat.type == ChatType.PRIVATE:

        selected_shortener = query.data.split('_')[1]
        res = await set_shortener(client.database, query.message.chat.id ,selected_shortener)

        if res:

            data = supported_shorteners[selected_shortener]

            reply_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('GET API TOKEN', url=data['api_key_page_url'])
                    ],
                    [
                        InlineKeyboardButton('CHANGE SHORTENER', callback_data='change_shortener')
                    ]
                ]
            )

            reply_text = (
                f'Great choice **{query.from_user.first_name}**, Your selected **URL Shortener** is '
                f'**{selected_shortener}**.\n\nNow click on the below button to get your **API Token** '
                'then send me your **API Token** in this format <pre>/api API_Token</pre>'
            )

        else:

            logger.error('Failed to set shortener')

            reply_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('TRY AGAIN', callback_data=query.data)
                    ],
                    [
                        InlineKeyboardButton('CHANGE SHORTENER', callback_data='change_shortener')
                    ]
                ]
            )

            reply_text = (
                f'Failed to set **{selected_shortener}** as default **URL Shortener** for your account. '
                'Please **Try Again** and if it continues to occur, Kindly contact us **[here](https://t.me/crebuo)**'
            )

        return await query.message.edit_text(
            text=reply_text,
            reply_markup=reply_markup
        )


    elif query.data.startswith('cnv'):

        async def progress_tracker(current, total, res, process_name):
            global prev_edit

            if time.time() - prev_edit > 5 and total != 0:
                await res.edit_text(
                    f'{process_name} - <pre>{((current / total) * 100):.2f} %</pre>'
                )
                prev_edit = time.time()


        data = query.data
        file_id = data.split('_')[1]
        # file_id = (await get_file_details(file_id))[0].file_id

        if data[4] == 'p':
            protect = True
        elif data[4] == 'n':
            protect = False

        info = await get_file_details(file_id)

        file = info[0]
        title = file.file_name
        size = get_size(file.file_size)
        f_type = file.file_type
        file_id = file.file_id

        f_caption = file.caption

        if CUSTOM_FILE_CAPTION:
            try:
                f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)

        if f_caption is None:
            f_caption = title

        if data[3] == 'v':

            if f_type != 'video':

                try:

                    unique_file_name = f"vid_{file_id}.{title.split(' ')[-1]}"

                    res = await query.message.edit_text('Downloading...')
                    print(res)

                    saved_file = await client.download_media(
                        file_id,
                        file_name=unique_file_name,
                        progress=progress_tracker,
                        progress_args=(res, 'Downloading')
                    )
                    try:
                        duration = int(await get_duration(saved_file))
                    except:
                        duration = 0

                    await res.edit_text('Uploading...')

                    delivered_file = await client.send_video(
                        DELIVERY_CHANNEL,
                        saved_file,
                        width=320,
                        height=180,
                        file_name=title,
                        duration=duration,
                        caption=f_caption,
                        protect_content=protect,
                        thumb='assets/thumb.jpg',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton('SUBSCRIBE', url='https://youtube.com/@gillharyana')
                        ]]),
                        progress=progress_tracker,
                        progress_args=(res, 'Uploading')
                    )

                except Exception as e:
                    print(e)

                finally:
                    os.remove(f'downloads/{unique_file_name}')

            else:
                delivered_file = await client.send_cached_media(
                    DELIVERY_CHANNEL,
                    file_id,
                    caption=f_caption,
                    protect_content=protect,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton('SUBSCRIBE', url='https://youtube.com/@gillharyana')
                    ]])
                )
            
        elif data[3] == 'd':

            if f_type != 'document':

                try:
                
                    unique_file_name = f"vid_{file_id}.{title.split(' ')[-1]}"

                    res = await query.message.edit_text('Downloading...')

                    saved_file = await client.download_media(
                        file_id,
                        file_name=unique_file_name,
                        progress=progress_tracker,
                        progress_args=(res, 'Downloading')
                    )

                    await res.edit_text('Uploading...')

                    delivered_file = await client.send_document(
                        DELIVERY_CHANNEL,
                        saved_file,
                        file_name=title,
                        caption=f_caption,
                        protect_content=protect,
                        thumb='assets/thumb.jpg',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton('SUBSCRIBE', url='https://youtube.com/@gillharyana')
                        ]]),
                        progress=progress_tracker,
                        progress_args=(res, 'Uploading')
                    )

                except Exception as e:
                    print(e)

                finally:
                    os.remove(f'downloads/{unique_file_name}')

            else:
                print(file_id)
                delivered_file = await client.send_cached_media(
                    DELIVERY_CHANNEL,
                    file_id,
                    caption=f_caption,
                    protect_content=protect,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton('SUBSCRIBE', url='https://youtube.com/@gillharyana')
                    ]])
                )

        invite_link = await get_invite_link(client)
        post_link = f"https://t.me/c/{str(DELIVERY_CHANNEL)[4:]}/{delivered_file.id}"

        reply_markup = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton('Join Channel', url=invite_link),
                InlineKeyboardButton('Get Your File', url=post_link)
            ]]
        )

        response_text = (
            'First **Join Channel** if you are not already Joined. '
            'Then click on **Get Your File** to access the requested file.\n\n'
            '**Note** - This message will be deleted in **2 Minutes**'
        )

        response = await query.message.edit_text(
            text=response_text,
            reply_markup=reply_markup
        )

        if response and delivered_file:

            await asyncio.sleep(FILE_DELETE_SECONDS)  
            await delivered_file.delete()
            await response.delete()

            print('Both file and links has been deleted from channel and user chat.')

        return

    await query.answer('𝙿𝙻𝙴𝙰𝚂𝙴 𝚂𝙷𝙰𝚁𝙴 𝙰𝙽𝙳 𝚂𝚄𝙿𝙿𝙾𝚁𝚃')


async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if 2 < len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    pre = 'filep' if settings['file_secure'] else 'file'

    #Added 
    end_point, api_key = '', ''

    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        down_user = await get_down_user(client.database, message.chat.id)

        if down_user:
            user_cred = await get_user_creds(client.database, down_user)

            if user_cred:
                shortener, api_key = user_cred
                print(shortener)
                end_point = supported_shorteners[shortener]['api_url']
                print(end_point)

    if not (end_point and api_key):
        short = await get_earn_status(client.database)

        if short:
            end_point, api_key = URL_SHORTENER_END_POINT, URL_SHORTENER_API_KEY

    print(end_point, api_key)

    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}", 
                    url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file.file_unique_id}", end_point, api_key)
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}", 
                    url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file.file_unique_id}", end_point, api_key)
                ),
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}", 
                    url=await get_shortlink(f"https://telegram.dog/{temp.U_NAME}?start=files_{file.file_unique_id}", end_point, api_key)
                ),
            ]
            for file in files
        ]

    btn.insert(0,
        [
            InlineKeyboardButton(text="⚡ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ⚡", url='https://t.me/MovieGrade')
        ]
    )

    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"🗓 1/{math.ceil(int(total_results) / 10)}", callback_data="pages"),
             InlineKeyboardButton(text="𝗡𝗲𝘅𝘁 ⏩", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="🗓 1/1", callback_data="pages")]
        )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"Rᴇǫᴜᴇsᴛᴇᴅ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ : <code>{search}</code>\n\n\n😌 ɪꜰ ᴛʜᴇ ᴍᴏᴠɪᴇ ʏᴏᴜ ᴀʀᴇ ʟᴏᴏᴋɪɴɢ ꜰᴏʀ ɪs ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ ᴛʜᴇɴ ʟᴇᴀᴠᴇ ᴀ ᴍᴇssᴀɢᴇ ʙᴇʟᴏᴡ 😌 \n\nᴇxᴀᴍᴘʟᴇ : \n\nᴇɴᴛᴇʀ ʏᴏᴜʀ ᴍᴏᴠɪᴇ ɴᴀᴍᴇ (ʏᴇᴀʀ) ᴛᴀɢ @admin"
    if imdb and imdb.get('poster'):
        try:
            hehe =  await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                      reply_markup=InlineKeyboardMarkup(btn))
            if SELF_DELETE:
                await asyncio.sleep(SELF_DELETE_SECONDS)
                await hehe.delete()

        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            hmm = await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
            if SELF_DELETE:
                await asyncio.sleep(SELF_DELETE_SECONDS)
                await hmm.delete()
        except Exception as e:
            logger.exception(e)
            fek = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
            if SELF_DELETE:
                await asyncio.sleep(SELF_DELETE_SECONDS)
                await fek.delete()
    else:
        fuk = await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
        if SELF_DELETE:
            await asyncio.sleep(SELF_DELETE_SECONDS)
            await fuk.delete()

async def advantage_spell_chok(msg):
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    query = query.strip() + " movie"
    g_s = await search_gagala(query)
    g_s += await search_gagala(msg.text)
    gs_parsed = []
    if not g_s:
        k = await msg.reply("I couldn't find any movie in that name.")
        await asyncio.sleep(8)
        await k.delete()
        return
    regex = re.compile(r".*(imdb|wikipedia).*", re.IGNORECASE)  # look for imdb / wiki results
    gs = list(filter(regex.match, g_s))
    gs_parsed = [re.sub(
        r'\b(\-([a-zA-Z-\s])\-\simdb|(\-\s)?imdb|(\-\s)?wikipedia|\(|\)|\-|reviews|full|all|episode(s)?|film|movie|series)',
        '', i, flags=re.IGNORECASE) for i in gs]
    if not gs_parsed:
        reg = re.compile(r"watch(\s[a-zA-Z0-9_\s\-\(\)]*)*\|.*",
                         re.IGNORECASE)  # match something like Watch Niram | Amazon Prime
        for mv in g_s:
            match = reg.match(mv)
            if match:
                gs_parsed.append(match.group(1))
    user = msg.from_user.id if msg.from_user else 0
    movielist = []
    gs_parsed = list(dict.fromkeys(gs_parsed))  # removing duplicates https://stackoverflow.com/a/7961425
    if len(gs_parsed) > 3:
        gs_parsed = gs_parsed[:3]
    if gs_parsed:
        for mov in gs_parsed:
            imdb_s = await get_poster(mov.strip(), bulk=True)  # searching each keyword in imdb
            if imdb_s:
                movielist += [movie.get('title') for movie in imdb_s]
    movielist += [(re.sub(r'(\-|\(|\)|_)', '', i, flags=re.IGNORECASE)).strip() for i in gs_parsed]
    movielist = list(dict.fromkeys(movielist))  # removing duplicates
    if not movielist:
        k = await msg.reply("I couldn't find anything related to that. Check your spelling")
        await asyncio.sleep(8)
        await k.delete()
        return
    SPELL_CHECK[msg.id] = movielist
    btn = [[
        InlineKeyboardButton(
            text=movie.strip(),
            callback_data=f"spolling#{user}#{k}",
        )
    ] for k, movie in enumerate(movielist)]
    btn.append([InlineKeyboardButton(text="Close", callback_data=f'spolling#{user}#close_spellcheck')])
    await msg.reply("I couldn't find anything related to that\nDid you mean any one of these?",
                    reply_markup=InlineKeyboardMarkup(btn),
                    quote=True)


async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(
                                group_id, 
                                reply_text, 
                                disable_web_page_preview=True,
                                reply_to_message_id=reply_id)
                        else:
                            button = eval(btn)
                            await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
   
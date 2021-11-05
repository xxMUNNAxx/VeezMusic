# Copyright (C) 2021 VeezMusicProject

from asyncio import QueueEmpty

from callsmusic import callsmusic
from callsmusic.queues import queues
from config import BOT_USERNAME, que
from cache.admins import admins
from handlers.play import cb_admin_check
from helpers.channelmusic import get_chat_id
from helpers.dbtools import delcmd_is_on, delcmd_off, delcmd_on, handle_user_status
from helpers.decorators import authorized_users_only, errors
from helpers.filters import command, other_filters
from pyrogram import Client, filters
from pytgcalls.types.input_stream import InputAudioStream
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


@Client.on_message()
async def _(bot: Client, cmd: Message):
    await handle_user_status(bot, cmd)


# Back Button
BACK_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🔙 Go Back", callback_data="cbback")]]
)

# @Client.on_message(filters.text & ~filters.private)
# async def delcmd(_, message: Message):
#    if await delcmd_is_on(message.chat.id) and message.text.startswith("/") or message.text.startswith("!") or message.text.startswith("."):
#        await message.delete()
#    await message.continue_propagation()

# remove the ( # ) if you want the auto del cmd feature is on


@Client.on_message(command(["reload", f"reload@{BOT_USERNAME}"]) & other_filters)
async def update_admin(client, message):
    global admins
    new_admins = []
    new_ads = await client.get_chat_members(message.chat.id, filter="administrators")
    for u in new_ads:
        new_admins.append(u.user.id)
    admins[message.chat.id] = new_admins
    await message.reply_text(
        "✅ Bot **reloaded correctly !**\n✅ **Admin list** has been **updated !**"
    )


# Control Menu Of Player
@Client.on_message(command(["control", f"control@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def controlset(_, message: Message):
    await message.reply_text(
        "💡 **here is the control menu of bot :**",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏸ pause", callback_data="cbpause"),
                    InlineKeyboardButton("▶️ resume", callback_data="cbresume"),
                ],
                [
                    InlineKeyboardButton("⏩ skip", callback_data="cbskip"),
                    InlineKeyboardButton("⏹ stop", callback_data="cbend"),
                ],
                [InlineKeyboardButton("⛔ anti cmd", callback_data="cbdelcmds")],
                [InlineKeyboardButton("🗑 Close", callback_data="close")],
            ]
        ),
    )


@Client.on_message(command(["pause", f"pause@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def pause(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        try:
            await callsmusic.pytgcalls.pause_stream(chat_id)
            await message.reply_text(
                "⏸ **Track paused.**\n\n• **To resume the playback, use the**\n» /resume command."
            )
        except Exception as e:
            await.message.reply(f"🚫 **error:**\n\n`{e}`")
    else:
         await message.reply("❌ **nothing in streaming**")
        


@Client.on_message(command(["resume", f"resume@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def resume(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        try:
            await callsmusic.pytgcalls.resume_stream(chat_id)
            await message.reply_text(
                "▶️ **Track resumed.**\n\n• **To pause the playback, use the**\n» /pause command."
            )
        except Exception as e:
            await message.reply(f"🚫 **error:**\n\n`{e}`")
    else:
        await message.reply("❌ **nothing in streaming**")


@Client.on_message(command(["end", f"end@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def stop(_, message: Message):
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        try:
            queues.clear(chat_id)
        except QueueEmpty:
            pass
        try:
            await callsmusic.pytgcalls.leave_group_call(chat_id)
            await message.reply_text("✅ **music playback has ended**")
        except Exception as e:
            await message.reply(f"🚫 **error:**\n\n`{e}`")
    else:
        await m.reply("❌ nothing is currently playing")


@Client.on_message(command(["skip", f"skip@{BOT_USERNAME}"]) & other_filters)
@errors
@authorized_users_only
async def skip(_, message: Message):
    global que
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.pytgcalls.active_calls:
        try:
            queues.task_done(chat_id)
        except Exception as e:
            await message.reply(f"🚫 **error:**\n\n`{e}`")
    else:
        await m.reply("❌ nothing is currently playing") 
        
        if queues.is_empty(chat_id):
            await callsmusic.pytgcalls.leave_group_call(chat_id)
        else:
            await callsmusic.pytgcalls.change_stream(
                chat_id, 
                InputAudioStream(
                    queues.get(chat_id)["file"],
                ),
            )

    qeue = que.get(chat_id)
    if qeue:
        qeue.pop(0)
    if not qeue:
        return
    await message.reply_text("⏭ **You've skipped to the next song.**")


@Client.on_message(command(["auth", f"auth@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def authenticate(client, message):
    global admins
    if not message.reply_to_message:
        return await message.reply("💡 reply to message to authorize user !")
    if message.reply_to_message.from_user.id not in admins[message.chat.id]:
        new_admins = admins[message.chat.id]
        new_admins.append(message.reply_to_message.from_user.id)
        admins[message.chat.id] = new_admins
        await message.reply(
            "🟢 user authorized.\n\nfrom now on, that's user can use the admin commands."
        )
    else:
        await message.reply("✅ user already authorized!")


@Client.on_message(command(["unauth", f"deauth@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def deautenticate(client, message):
    global admins
    if not message.reply_to_message:
        return await message.reply("💡 reply to message to deauthorize user !")
    if message.reply_to_message.from_user.id in admins[message.chat.id]:
        new_admins = admins[message.chat.id]
        new_admins.remove(message.reply_to_message.from_user.id)
        admins[message.chat.id] = new_admins
        await message.reply(
            "🔴 user deauthorized.\n\nfrom now that's user can't use the admin commands."
        )
    else:
        await message.reply("✅ user already deauthorized!")


# this is a anti cmd feature
@Client.on_message(command(["delcmd", f"delcmd@{BOT_USERNAME}"]) & other_filters)
@authorized_users_only
async def delcmdc(_, message: Message):
    if len(message.command) != 2:
        return await message.reply_text(
            "read the /help message to know how to use this command"
        )
    status = message.text.split(None, 1)[1].strip()
    status = status.lower()
    chat_id = message.chat.id
    if status == "on":
        if await delcmd_is_on(message.chat.id):
            return await message.reply_text("✅ already activated")
        await delcmd_on(chat_id)
        await message.reply_text("🟢 activated successfully")
    elif status == "off":
        await delcmd_off(chat_id)
        await message.reply_text("🔴 disabled successfully")
    else:
        await message.reply_text(
            "read the /help message to know how to use this command"
        )


# music player callbacks (control by buttons feature)


@Client.on_callback_query(filters.regex("cbpause"))
@cb_admin_check
async def cbpause(_, query: CallbackQuery):
    get_chat_id(query.message.chat)
    if query.message.chat.id in callsmusic.pytgcalls.active_calls:
        try:
            await callsmusic.pytgcalls.pause_stream(query.message.chat.id)
            await query.edit_message_text(
                "⏸ music playback has been paused", reply_markup=BACK_BUTTON
            )
         
        except Exception as e:
            await message.reply(f"🚫 **error:**\n\n`{e}`")
    else:
        await query.edit_message_text(
            "❌ **no music is currently playing**", reply_markup=BACK_BUTTON
        )

@Client.on_callback_query(filters.regex("cbresume"))
@cb_admin_check
async def cbresume(_, query: CallbackQuery):
    get_chat_id(query.message.chat)
    if query.message.chat.id in callsmusic.pytgcalls.active_calls:
        try:
            await callsmusic.pytgcalls.resume_stream(query.message.chat.id)
            await query.edit_message_text(
                "▶️ music playback has been resumed", reply_markup=BACK_BUTTON
            )
        except Exception as e:
            await message.reply()
    else:
        await query.edit_message_text(
            "❌ **no music is currently paused**", reply_markup=BACK_BUTTON
        )      
     

@Client.on_callback_query(filters.regex("cbend"))
@cb_admin_check
async def cbend(_, query: CallbackQuery):
    get_chat_id(query.message.chat)
    if query.message.chat.id in callsmusic.pytgcalls.active_calls:
        try:
            queues.clear(query.message.chat.id)
        except QueueEmpty:
            pass
        try:
            await callsmusic.pytgcalls.leave_group_call(query.message.chat.id)
            await query.edit_message_text(
                "✅ the music queue has been cleared and successfully left voice chat",
                reply_markup=BACK_BUTTON,
            )
        except Expection as e:
            await message.reply()
    else:
        await query.edit_message_text(
            "❌ **no music is currently playing**", reply_markup=BACK_BUTTON
        )

@Client.on_callback_query(filters.regex("cbskip"))
@cb_admin_check
async def cbskip(_, query: CallbackQuery):
    global que
    chat_id = get_chat_id(query.message.chat)
    if query.message.chat.id not in callsmusic.pytgcalls.active_calls:
        try:
            queues.task_done(query.message.chat.id)
        except Exception as e:
            await message.reply()
    else:
        await query.edit_message_text(
            "❌ **no music is currently playing**", reply_markup=BACK_BUTTON
        )
        
        if queues.is_empty(query.message.chat.id):
            await callsmusic.pytgcalls.leave_group_call(query.message.chat.id)
        else:
            await callsmusic.pytgcalls.change_stream(
                query.message.chat.id, 
                InputAudioStream(
                    queues.get(query.message.chat.id)["file"],
                ),
            )

    qeue = que.get(chat_id)
    if qeue:
        qeue.pop(0)
    if not qeue:
        return
    await query.edit_message_text(
        "⏭ **You've skipped to the next song**", reply_markup=BACK_BUTTON
    )

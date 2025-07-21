from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message, MessageEntity
from Aviyaa import app
from httpx import AsyncClient, Timeout
import html
import re

# -----------------------------------------------------------------
fetch = AsyncClient(
    http2=True,
    verify=False,
    headers={
        "Accept-Language": "id-ID",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edge/107.0.1418.42",
    },
    timeout=Timeout(20),
)

# ------------------------------------------------------------------------
class QuotlyException(Exception):
    pass

# Updated entity mapping for Pyrogram
_entities = {
    MessageEntity.PHONE: "phone_number",
    MessageEntity.MENTION: "mention",
    MessageEntity.BOLD: "bold",
    MessageEntity.CASHTAG: "cashtag",
    MessageEntity.STRIKETHROUGH: "strikethrough",
    MessageEntity.HASHTAG: "hashtag",
    MessageEntity.EMAIL: "email",
    MessageEntity.MENTION_NAME: "text_mention",
    MessageEntity.UNDERLINE: "underline",
    MessageEntity.URL: "url",
    MessageEntity.TEXT_LINK: "text_link",
    MessageEntity.BOT_COMMAND: "bot_command",
    MessageEntity.CODE: "code",
    MessageEntity.PRE: "pre",
    MessageEntity.SPOILER: "spoiler",
}

# --------------------------------------------------------------------------
async def get_message_sender_id(ctx: Message):
    if ctx.forward_date:
        if ctx.forward_sender_name:
            return 1
        elif ctx.forward_from:
            return ctx.forward_from.id
        elif ctx.forward_from_chat:
            return ctx.forward_from_chat.id
        else:
            return 1
    elif ctx.from_user:
        return ctx.from_user.id
    elif ctx.sender_chat:
        return ctx.sender_chat.id
    else:
        return 1

# -----------------------------------------------------------------------------------------
async def get_message_sender_name(ctx: Message):
    def clean_name(name):
        if not name:
            return "Deleted Account"
        name = html.escape(name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    try:
        if ctx.forward_date:
            if ctx.forward_sender_name:
                return clean_name(ctx.forward_sender_name)
            elif ctx.forward_from:
                name = ctx.forward_from.first_name or ""
                if ctx.forward_from.last_name:
                    name += f" {ctx.forward_from.last_name}"
                return clean_name(name)
            elif ctx.forward_from_chat:
                return clean_name(ctx.forward_from_chat.title or "")
        elif ctx.from_user:
            name = ctx.from_user.first_name or ""
            if ctx.from_user.last_name:
                name += f" {ctx.from_user.last_name}"
            return clean_name(name)
        elif ctx.sender_chat:
            return clean_name(ctx.sender_chat.title or "")
        return "Deleted Account"
    except Exception:
        return "Deleted Account"

# ---------------------------------------------------------------------------------------------------
async def get_message_sender_username(ctx: Message):
    try:
        if ctx.forward_date:
            if (not ctx.forward_sender_name and not ctx.forward_from and 
                ctx.forward_from_chat and ctx.forward_from_chat.username):
                return ctx.forward_from_chat.username
            elif (not ctx.forward_sender_name and not ctx.forward_from and 
                  ctx.forward_from_chat or ctx.forward_sender_name or not ctx.forward_from):
                return None
            else:
                return ctx.forward_from.username or None
        elif ctx.from_user and ctx.from_user.username:
            return ctx.from_user.username
        elif (ctx.from_user or ctx.sender_chat and 
              not ctx.sender_chat.username or not ctx.sender_chat):
            return None
        else:
            return ctx.sender_chat.username or None
    except Exception:
        return None

# ---------------------------------------------------------------------------------------------------
async def get_text_or_caption(ctx: Message):
    try:
        text = ctx.text or ctx.caption or ""
        text = html.escape(text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text
    except Exception:
        return ""

# ---------------------------------------------------------------------------------------------------
async def pyrogram_to_quotly(messages, is_reply):
    if not isinstance(messages, list):
        messages = [messages]
    
    payload = {
        "type": "quote",
        "format": "webp",
        "backgroundColor": "#1b1429",
        "width": 512,
        "height": 768,
        "scale": 2,
        "messages": [],
    }

    for message in messages:
        the_message_dict_to_append = {}
        try:
            if message.entities:
                the_message_dict_to_append["entities"] = [
                    {
                        "type": _entities.get(entity.type, entity.type),
                        "offset": entity.offset,
                        "length": entity.length,
                    }
                    for entity in message.entities
                    if entity.type in _entities
                ]
            elif message.caption_entities:
                the_message_dict_to_append["entities"] = [
                    {
                        "type": _entities.get(entity.type, entity.type),
                        "offset": entity.offset,
                        "length": entity.length,
                    }
                    for entity in message.caption_entities
                    if entity.type in _entities
                ]
            else:
                the_message_dict_to_append["entities"] = []
            
            the_message_dict_to_append["chatId"] = await get_message_sender_id(message)
            the_message_dict_to_append["text"] = await get_text_or_caption(message)
            the_message_dict_to_append["avatar"] = True
            
            the_message_dict_to_append["from"] = {
                "id": await get_message_sender_id(message),
                "first_name": await get_message_sender_name(message),
                "last_name": None,
                "username": await get_message_sender_username(message),
                "language_code": "en",
                "title": await get_message_sender_name(message),
                "name": await get_message_sender_name(message),
                "type": message.chat.type.name.lower() if message.chat else "private",
            }
            
            if message.reply_to_message and is_reply:
                try:
                    the_message_dict_to_append["replyMessage"] = {
                        "name": await get_message_sender_name(message.reply_to_message),
                        "text": await get_text_or_caption(message.reply_to_message),
                        "chatId": await get_message_sender_id(message.reply_to_message),
                    }
                except Exception:
                    the_message_dict_to_append["replyMessage"] = {}
            else:
                the_message_dict_to_append["replyMessage"] = {}
                
            payload["messages"].append(the_message_dict_to_append)
        except Exception as e:
            print(f"Error processing message: {e}")
            continue

    try:
        urls_to_try = [
            "https://bot.lyo.su/quote/generate",
            "https://quoteampi.onrender.com/generate"
        ]
        
        last_exception = None
        for url in urls_to_try:
            try:
                r = await fetch.post(url, json=payload)
                if not r.is_error:
                    return r.read()
                else:
                    last_exception = QuotlyException(r.json())
            except Exception as e:
                last_exception = e
        
        if last_exception:
            raise last_exception
        raise QuotlyException("All quote APIs failed")
    except Exception as e:
        raise QuotlyException(str(e))

# ------------------------------------------------------------------------------------------

def isArgInt(txt) -> list:
    count = txt
    try:
        count = int(count)
        return [True, count]
    except ValueError:
        return [False, 0]

# ---------------------------------------------------------------------------------------------------
@app.on_message(filters.command(["q", "quote"]) & filters.reply)
async def msg_quotly_cmd(self: app, ctx: Message):
    is_reply = False
    if ctx.command[0].endswith("r"):
        is_reply = True
        
    if len(ctx.text.split()) > 1:
        check_arg = isArgInt(ctx.command[1])
        if check_arg[0]:
            if check_arg[1] < 2 or check_arg[1] > 10:
                return await ctx.reply_text("Invalid range", del_in=6)
            try:
                messages = [
                    i
                    for i in await self.get_messages(
                        chat_id=ctx.chat.id,
                        message_ids=range(
                            ctx.reply_to_message.id,
                            ctx.reply_to_message.id + (check_arg[1] + 5)),
                        replies=-1,
                    )
                    if not i.empty and not i.media
                ]
                if not messages:
                    return await ctx.reply_text("No valid messages found", del_in=6)
            except Exception as e:
                return await ctx.reply_text(f"Error getting messages: {e}", del_in=6)
            
            try:
                make_quotly = await pyrogram_to_quotly(messages, is_reply=is_reply)
                bio_sticker = BytesIO(make_quotly)
                bio_sticker.name = "quote.webp"
                return await ctx.reply_sticker(bio_sticker)
            except Exception as e:
                return await ctx.reply_text(f"Error generating quote: {e}", del_in=6)
    
    try:
        messages_one = await self.get_messages(
            chat_id=ctx.chat.id, message_ids=ctx.reply_to_message.id, replies=-1
        )
        messages = [messages_one]
    except Exception as e:
        return await ctx.reply_text(f"Error getting message: {e}", del_in=6)
    
    try:
        make_quotly = await pyrogram_to_quotly(messages, is_reply=is_reply)
        bio_sticker = BytesIO(make_quotly)
        bio_sticker.name = "quote.webp"
        return await ctx.reply_sticker(bio_sticker)
    except Exception as e:
        return await ctx.reply_text(f"ERROR: {e}", del_in=6)
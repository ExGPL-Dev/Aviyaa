from io import BytesIO
import os
import requests
from aiohttp import ClientSession
from pyrogram import filters
from pyrogram.types import *
from Aviyaa import app

button = InlineKeyboardMarkup(
    [[InlineKeyboardButton("CLOSE", callback_data="close_data")]]
)

aiohttpsession = ClientSession()

# Load NSFW words from text file
def load_nsfw_list():
    path = "Aviyaa/assets/nsfw-list.txt"
    if not os.path.exists(path):
        return []
    with open(path, "r") as file:
        return [line.strip().lower() for line in file if line.strip()]

NSFW_KEYWORDS = load_nsfw_list()

def is_nsfw_url(url: str):
    return any(keyword in url.lower() for keyword in NSFW_KEYWORDS)

async def take_screenshot(url: str, full: bool = False):
    url = "https://" + url if not url.startswith(("http://", "https://")) else url
    api_url = f"https://api.screenshotone.com/take?url={url}"
    if full:
        api_url += "&full_page=true"

    try:
        async with aiohttpsession.get(api_url) as resp:
            if resp.status != 200:
                return None
            image_data = await resp.read()
            file = BytesIO(image_data)
            file.name = "webss.jpg"
            return file
    except Exception:
        return None

async def eor(msg: Message, **kwargs):
    func = (
        (msg.edit_text if msg.from_user.is_self else msg.reply)
        if msg.from_user
        else msg.reply
    )
    return await func(**kwargs)

@app.on_message(filters.command(["webss"]))
async def take_ss(_, message: Message):
    if len(message.command) < 2:
        return await eor(
            message,
            text="**👉 Enter command with correct url**\n\n```Example:\n/webss https://pynoxi.com\n```",
            disable_web_page_preview=True,
        )

    url = message.text.split(None, 1)[1]
    full = False

    if len(message.command) == 3:
        full = message.text.split(None, 2)[2].lower().strip() in [
            "yes", "y", "1", "true"
        ]

    # NSFW check
    if is_nsfw_url(url):
        try:
            # Attempt to delete the user's message (if bot is admin)
            await message.delete()
        except Exception:
            pass  # Silently ignore if bot isn't admin or can't delete

        report = (
            f"/report\n\n🚫 **Adult or NSFW websites are not allowed**\n\n"
            f"[{message.from_user.id}](tg://user?id={message.from_user.id}) Sent NSFW URL."
        )
        await app.send_message(chat_id=message.chat.id, text=report)
        return  # Do not respond to user

    m = await eor(message, text="**Taking screenshot...**")

    try:
        photo = await take_screenshot(url, full)
        if not photo:
            return await m.edit("**Screenshot Failed.**")

        await m.edit("**Screenshot Uploading...**")
        await message.reply_photo(photo, reply_markup=button)
        await m.delete()
    except Exception as e:
        await m.edit(str(e))

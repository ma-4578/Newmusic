#Khithlainhtet

from pyrogram import enums, filters, types # enums ကို import ထည့်ထားပါတယ်

from Newmusic import app, db, lang
from Newmusic.helpers import utils


@app.on_message(filters.command(["addsudo", "delsudo", "rmsudo"]) & filters.user(app.owner))
@lang.language()
async def _sudo(_, m: types.Message):
    user = await utils.extract_user(m)
    if not user:
        return await m.reply_text(m.lang["user_not_found"], parse_mode=enums.ParseMode.HTML)

    if m.command[0] == "addsudo":
        if user.id in app.sudoers:
            return await m.reply_text(m.lang["sudo_already"].format(user.mention), parse_mode=enums.ParseMode.HTML)

        app.sudoers.add(user.id)
        await db.add_sudo(user.id)
        await m.reply_text(m.lang["sudo_added"].format(user.mention), parse_mode=enums.ParseMode.HTML)
    else:
        if user.id not in app.sudoers:
            return await m.reply_text(m.lang["sudo_not"].format(user.mention), parse_mode=enums.ParseMode.HTML)

        app.sudoers.discard(user.id)
        await db.del_sudo(user.id)
        await m.reply_text(m.lang["sudo_removed"].format(user.mention), parse_mode=enums.ParseMode.HTML)


o_mention = None

@app.on_message(filters.command(["listsudo", "sudolist"]))
@lang.language()
async def _listsudo(_, m: types.Message):
    global o_mention
    sent = await m.reply_text(m.lang["sudo_fetching"], parse_mode=enums.ParseMode.HTML)

    if not o_mention:
        o_mention = (await app.get_users(app.owner)).mention
    txt = m.lang["sudo_owner"].format(o_mention)
    sudoers = await db.get_sudoers()
    if sudoers:
        txt += m.lang["sudo_users"]

    for user_id in sudoers:
        try:
            user = (await app.get_users(user_id)).mention
            txt += f"\n- {user}"
        except Exception:
            continue

    # edit_text မှာ parse_mode ထည့်ပေးထားလို့ Premium Emoji တွေ ပေါ်ပါလိမ့်မယ်
    await sent.edit_text(txt, parse_mode=enums.ParseMode.HTML)

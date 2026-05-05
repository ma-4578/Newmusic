#Khithlainhtet

from pathlib import Path
from pyrogram import enums, filters, types # enums ကို import ထည့်ထားပါတယ်

from Newmusic import anon, app, config, db, lang, queue, tg, yt
from Newmusic.helpers import buttons, utils
from Newmusic.helpers._play import checkUB


def playlist_to_queue(chat_id: int, tracks: list) -> str:
    text = "<blockquote expandable>"
    for track in tracks:
        pos = queue.add(chat_id, track)
        text += f"<b>{pos}.</b> {track.title}\n"
    text = text[:1948] + "</blockquote>"
    return text


@app.on_message(
    filters.command(["play", "playforce", "vplay", "vplayforce"])
    & filters.group
    & ~app.bl_users
)
@lang.language()
@checkUB
async def play_hndlr(
    _,
    m: types.Message,
    force: bool = False,
    m3u8: bool = False,
    video: bool = False,
    url: str = None,
) -> None:
    # Searching message မှာ HTML parse mode ထည့်ပါတယ်
    sent = await m.reply_text(m.lang["play_searching"], parse_mode=enums.ParseMode.HTML)
    file = None
    mention = m.from_user.mention
    media = tg.get_media(m.reply_to_message) if m.reply_to_message else None
    tracks = []
    is_playlist = False

    if media:
        setattr(sent, "lang", m.lang)
        file = await tg.download(m.reply_to_message, sent)

    elif m3u8:
        file = await tg.process_m3u8(url, sent.id, video)

    elif url:
        if "playlist" in url:
            is_playlist = True
            await sent.edit_text(m.lang["playlist_fetch"], parse_mode=enums.ParseMode.HTML)
            tracks = await yt.playlist(config.PLAY_LIMIT, mention, url, video)

            if not tracks:
                return await sent.edit_text(m.lang["playlist_error"], parse_mode=enums.ParseMode.HTML)

            file = tracks.pop(0)
            file.message_id = sent.id
        else:
            file = await yt.search(url, sent.id, video=video)

        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT),
                parse_mode=enums.ParseMode.HTML
            )

    elif len(m.command) >= 2:
        query = " ".join(m.command[1:])
        file = await yt.search(query, sent.id, video=video)
        if not file:
            return await sent.edit_text(
                m.lang["play_not_found"].format(config.SUPPORT_CHAT),
                parse_mode=enums.ParseMode.HTML
            )

    if not file:
        return await sent.edit_text(m.lang["play_usage"], parse_mode=enums.ParseMode.HTML)

    if file.duration_sec > config.DURATION_LIMIT:
        return await sent.edit_text(
            m.lang["play_duration_limit"].format(config.DURATION_LIMIT // 60),
            parse_mode=enums.ParseMode.HTML
        )

    if await db.is_logger():
        await utils.play_log(m, sent.link, file.title, file.duration)

    file.user = mention
    if force:
        queue.force_add(m.chat.id, file)
    else:
        position = queue.add(m.chat.id, file)

        if position != 0 or await db.get_call(m.chat.id):
            # Queue message မှာ Premium Emoji ပေါ်အောင် parse mode ထည့်ထားပါတယ်
            await sent.edit_text(
                m.lang["play_queued"].format(
                    position,
                    file.url,
                    file.title,
                    file.duration,
                    m.from_user.mention,
                ),
                reply_markup=buttons.play_queued(
                    m.chat.id, file.id, m.lang["play_now"]
                ),
                parse_mode=enums.ParseMode.HTML
            )
            if tracks:
                added = playlist_to_queue(m.chat.id, tracks)
                await app.send_message(
                    chat_id=m.chat.id,
                    text=m.lang["playlist_queued"].format(len(tracks)) + added,
                    parse_mode=enums.ParseMode.HTML
                )
            return

    if not file.file_path:
        cached = next(
            (
                f"downloads/{file.id}.{ext}"
                for ext in ("mp4", "webm", "mp3", "m4a")
                if Path(f"downloads/{file.id}.{ext}").exists()
            ),
            None,
        )
        if cached:
            file.file_path = cached
        else:
            await sent.edit_text(m.lang["play_downloading"], parse_mode=enums.ParseMode.HTML)
            file.file_path = await yt.download(file.id, video=video)

    try:
        await anon.play_media(chat_id=m.chat.id, message=sent, media=file)
    except Exception:
        if is_playlist and tracks and not force:
            try:
                queue.remove(m.chat.id, file)
            except Exception:
                pass
        raise

    if not tracks:
        return

    added = playlist_to_queue(m.chat.id, tracks)
    await app.send_message(
        chat_id=m.chat.id,
        text=m.lang["playlist_queued"].format(len(tracks)) + added,
        parse_mode=enums.ParseMode.HTML
    )

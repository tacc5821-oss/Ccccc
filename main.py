#!/usr/bin/env python3
"""
Telegram group "bluff" game bot.

Features:
- Lobby with Join / Start (max 10, min 3)
- Sequential nickname registration with a 1-minute timeout per player
- Random secret Killer with DM control panel (Curse Others, Self Curse, Remove Curse, Fake Alert)
- Cursed players' group messages are deleted after 0.5s and replaced with "🤐 [Nickname] စကားပြောလို့မရပါ"
- Vote phase (/vote) with a 2-minute timeout. Tie => Killer wins (no elimination).
- Eliminated players are marked inactive and cannot be cursed or vote
- SQLite persistence for games, players, cursed status, and votes
"""

import asyncio
import logging
import os
import random
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Database helpers ----------
def init_db():
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            chat_id INTEGER PRIMARY KEY,
            state TEXT,
            owner_id INTEGER,
            registration_index INTEGER,
            waiting_user_id INTEGER,
            join_message_id INTEGER,
            join_message_text TEXT,
            killer_id INTEGER,
            vote_message_id INTEGER,
            vote_deadline INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            nickname TEXT,
            role TEXT,
            active INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cursed (
            chat_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS votes (
            chat_id INTEGER,
            voter_id INTEGER,
            target_id INTEGER,
            PRIMARY KEY (chat_id, voter_id)
        )
        """
    )
    con.commit()
    con.close()


def db_get_game_row(chat_id: int) -> Optional[Tuple]:
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT * FROM games WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    con.close()
    return row


def db_upsert_game_row(
    chat_id: int,
    state: str,
    owner_id: Optional[int],
    registration_index: int,
    waiting_user_id: Optional[int],
    join_message_id: Optional[int],
    join_message_text: Optional[str],
    killer_id: Optional[int],
    vote_message_id: Optional[int],
    vote_deadline: Optional[int],
):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO games(chat_id, state, owner_id, registration_index, waiting_user_id, join_message_id, join_message_text, killer_id, vote_message_id, vote_deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            state=excluded.state,
            owner_id=excluded.owner_id,
            registration_index=excluded.registration_index,
            waiting_user_id=excluded.waiting_user_id,
            join_message_id=excluded.join_message_id,
            join_message_text=excluded.join_message_text,
            killer_id=excluded.killer_id,
            vote_message_id=excluded.vote_message_id,
            vote_deadline=excluded.vote_deadline
        """,
        (
            chat_id,
            state,
            owner_id,
            registration_index,
            waiting_user_id,
            join_message_id,
            join_message_text,
            killer_id,
            vote_message_id,
            vote_deadline,
        ),
    )
    con.commit()
    con.close()


def db_delete_game(chat_id: int):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM games WHERE chat_id = ?", (chat_id,))
    cur.execute("DELETE FROM players WHERE chat_id = ?", (chat_id,))
    cur.execute("DELETE FROM cursed WHERE chat_id = ?", (chat_id,))
    cur.execute("DELETE FROM votes WHERE chat_id = ?", (chat_id,))
    con.commit()
    con.close()


def db_upsert_player(chat_id: int, user_id: int, username: str, nickname: Optional[str], role: str, active: bool):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO players(chat_id, user_id, username, nickname, role, active)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET
            username=excluded.username,
            nickname=excluded.nickname,
            role=excluded.role,
            active=excluded.active
        """,
        (chat_id, user_id, username, nickname, role, int(active)),
    )
    con.commit()
    con.close()


def db_get_players(chat_id: int) -> List[Tuple]:
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT user_id, username, nickname, role, active FROM players WHERE chat_id = ? ORDER BY rowid", (chat_id,))
    rows = cur.fetchall()
    con.close()
    return rows


def db_delete_player(chat_id: int, user_id: int):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM players WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    cur.execute("DELETE FROM cursed WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    cur.execute("DELETE FROM votes WHERE chat_id = ? AND voter_id = ?", (chat_id, user_id))
    cur.execute("DELETE FROM votes WHERE chat_id = ? AND target_id = ?", (chat_id, user_id))
    con.commit()
    con.close()


def db_set_cursed(chat_id: int, user_id: int):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO cursed(chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
    con.commit()
    con.close()


def db_remove_cursed(chat_id: int, user_id: int):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cursed WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    con.commit()
    con.close()


def db_get_cursed_set(chat_id: int) -> Set[int]:
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT user_id FROM cursed WHERE chat_id = ?", (chat_id,))
    rows = cur.fetchall()
    con.close()
    return {r[0] for r in rows}


def db_add_vote(chat_id: int, voter_id: int, target_id: int):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO votes(chat_id, voter_id, target_id) VALUES (?, ?, ?)",
        (chat_id, voter_id, target_id),
    )
    con.commit()
    con.close()


def db_clear_votes(chat_id: int):
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM votes WHERE chat_id = ?", (chat_id,))
    con.commit()
    con.close()


def db_get_votes(chat_id: int) -> Dict[int, int]:
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT voter_id, target_id FROM votes WHERE chat_id = ?", (chat_id,))
    rows = cur.fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}


# ---------- In-memory model ----------
@dataclass
class Player:
    user_id: int
    username: str
    nickname: Optional[str] = None
    role: str = "villager"
    active: bool = True


@dataclass
class Game:
    chat_id: int
    state: str = "idle"  # idle, lobby, registration, in_game, voting, ended
    owner_id: Optional[int] = None
    players: List[Player] = field(default_factory=list)
    join_message_id: Optional[int] = None
    join_message_text: Optional[str] = None
    waiting_for_nickname_user_id: Optional[int] = None
    registration_index: int = 0
    cursed: Set[int] = field(default_factory=set)
    killer_id: Optional[int] = None
    vote_message_id: Optional[int] = None
    vote_deadline: Optional[int] = None

    # runtime-only tasks (not persisted)
    registration_task: Optional[asyncio.Task] = None
    voting_task: Optional[asyncio.Task] = None


# All active games in memory
GAMES: Dict[int, Game] = {}


# ---------- Utility functions ----------
def load_game_from_db(chat_id: int) -> Optional[Game]:
    row = db_get_game_row(chat_id)
    if not row:
        return None
    # row fields: chat_id, state, owner_id, registration_index, waiting_user_id,
    # join_message_id, join_message_text, killer_id, vote_message_id, vote_deadline
    _, state, owner_id, reg_idx, waiting_user_id, join_msg_id, join_msg_text, killer_id, vote_msg_id, vote_deadline = row
    g = Game(chat_id=chat_id)
    g.state = state
    g.owner_id = owner_id
    g.registration_index = reg_idx or 0
    g.waiting_for_nickname_user_id = waiting_user_id
    g.join_message_id = join_msg_id
    g.join_message_text = join_msg_text
    g.killer_id = killer_id
    g.vote_message_id = vote_msg_id
    g.vote_deadline = vote_deadline
    # load players
    rows = db_get_players(chat_id)
    for user_id, username, nickname, role, active in rows:
        g.players.append(Player(user_id=user_id, username=username, nickname=nickname, role=role, active=bool(active)))
    # cursed
    g.cursed = db_get_cursed_set(chat_id)
    return g


def save_game_to_db(game: Game):
    vote_deadline = game.vote_deadline
    db_upsert_game_row(
        chat_id=game.chat_id,
        state=game.state,
        owner_id=game.owner_id,
        registration_index=game.registration_index,
        waiting_user_id=game.waiting_for_nickname_user_id,
        join_message_id=game.join_message_id,
        join_message_text=game.join_message_text,
        killer_id=game.killer_id,
        vote_message_id=game.vote_message_id,
        vote_deadline=vote_deadline,
    )
    # players
    for p in game.players:
        db_upsert_player(game.chat_id, p.user_id, p.username, p.nickname, p.role, p.active)
    # cursed set
    # clear existing then insert current
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM cursed WHERE chat_id = ?", (game.chat_id,))
    for uid in game.cursed:
        cur.execute("INSERT OR IGNORE INTO cursed(chat_id, user_id) VALUES (?, ?)", (game.chat_id, uid))
    con.commit()
    con.close()


def remove_player_from_game(game: Game, user_id: int):
    # mark inactive in memory and DB
    for p in game.players:
        if p.user_id == user_id:
            p.active = False
            db_upsert_player(game.chat_id, p.user_id, p.username, p.nickname, p.role, p.active)
            break
    # remove votes referencing them
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM votes WHERE chat_id = ? AND voter_id = ?", (game.chat_id, user_id))
    cur.execute("DELETE FROM votes WHERE chat_id = ? AND target_id = ?", (game.chat_id, user_id))
    con.commit()
    con.close()


def active_players(game: Game) -> List[Player]:
    return [p for p in game.players if p.active]


def player_by_user_id(game: Game, user_id: int) -> Optional[Player]:
    return next((p for p in game.players if p.user_id == user_id), None)


def active_villagers_count(game: Game) -> int:
    return sum(1 for p in game.players if p.active and p.role != "killer")


def active_killers_count(game: Game) -> int:
    return sum(1 for p in game.players if p.active and p.role == "killer")


# ---------- Bot command & callback handlers ----------
async def start_game_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("This command only works in groups.")
        return

    # check admin
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        await update.message.reply_text("Only group Admin/Owner can start a game.")
        return

    # Create new game or reset existing
    game = GAMES.get(chat.id)
    if not game:
        game = load_game_from_db(chat.id) or Game(chat_id=chat.id)
        GAMES[chat.id] = game

    if game.state not in ("idle", "ended"):
        await update.message.reply_text("A game is already running in this chat.")
        return

    # initialize
    game.state = "lobby"
    game.owner_id = user.id
    game.players = []
    game.cursed = set()
    game.registration_index = 0
    game.waiting_for_nickname_user_id = None
    game.killer_id = None
    game.vote_message_id = None
    game.vote_deadline = None
    # persist
    save_game_to_db(game)

    text = "ဂိမ်းကစားမည့်သူများ - Join 🙋‍♂️\n(အများဆုံး 10 ယောက်၊ အနည်းဆုံး 3 ယောက်လိုအပ်ပါသည်)"
    join_button = InlineKeyboardButton("Join 🙋‍♂️", callback_data="join")
    start_button = InlineKeyboardButton("Start Game 🚀", callback_data="start_game")
    kb = InlineKeyboardMarkup([[join_button, start_button]])
    sent = await update.message.reply_text(text, reply_markup=kb)
    game.join_message_id = sent.message_id
    game.join_message_text = text
    save_game_to_db(game)
    await update.message.reply_text("Lobby opened. Players, press Join 🙋‍♂️")


async def join_or_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat = query.message.chat
    game = GAMES.get(chat.id) or (load_game_from_db(chat.id) or Game(chat_id=chat.id))
    GAMES[chat.id] = game

    if game.state != "lobby":
        await query.answer(text="Lobby is not active.")
        return

    if query.data == "join":
        if player_by_user_id(game, user.id):
            await query.answer(text="You already joined.")
            return
        if len(game.players) >= 10:
            await query.answer(text="Lobby is full.")
            return
        username = user.username or (user.first_name or f"user{user.id}")
        p = Player(user_id=user.id, username=username)
        game.players.append(p)
        db_upsert_player(game.chat_id, p.user_id, p.username, p.nickname, p.role, p.active)
        save_game_to_db(game)
        count = len(game.players)
        new_text = f"ဂိမ်းကစားမည့်သူများ - {count} joined\n(အများဆုံး 10 ယောက်၊ အနည်းဆုံး 3 ယောက်လိုအပ်ပါသည်)"
        if count >= 10:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Full (10)", callback_data="noop")]])
        else:
            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Join 🙋‍♂️", callback_data="join"),
                        InlineKeyboardButton("Start Game 🚀", callback_data="start_game"),
                    ]
                ]
            )
        try:
            await query.edit_message_text(new_text, reply_markup=kb)
            game.join_message_text = new_text
            game.join_message_id = query.message.message_id
            save_game_to_db(game)
        except Exception:
            pass
        await query.answer(text=f"Joined as @{p.username}")

    elif query.data == "start_game":
        # verify admin
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            await query.answer(text="Only Admin/Owner can start the game.")
            return
        if len(game.players) < 3:
            await query.answer(text="At least 3 players are required to start.")
            return
        # move to registration
        game.state = "registration"
        save_game_to_db(game)
        await query.edit_message_text("Registration started. Bot will ask for nicknames one-by-one.")
        # begin sequential nickname registration
        await ask_next_nickname(context, game)


async def ask_next_nickname(context: ContextTypes.DEFAULT_TYPE, game: Game):
    # If registration finished
    while game.registration_index < len(game.players) and not game.players[game.registration_index].active:
        game.registration_index += 1

    if game.registration_index >= len(game.players):
        await finish_registration(context, game)
        return

    player = game.players[game.registration_index]
    chat_id = game.chat_id
    mention = f"@{player.username}"
    sent = await context.bot.send_message(chat_id=chat_id, text=f"{mention} ကျေးဇူးပြု၍ Nickname ပို့ပါ။")
    game.waiting_for_nickname_user_id = player.user_id
    save_game_to_db(game)

    # schedule timeout for this player's nickname
    if game.registration_task and not game.registration_task.done():
        game.registration_task.cancel()
    game.registration_task = asyncio.create_task(registration_timeout(context, game.chat_id, player.user_id))


async def registration_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    await asyncio.sleep(config.NICKNAME_TIMEOUT)
    game = GAMES.get(chat_id)
    if not game:
        return
    if game.state != "registration":
        return
    if game.waiting_for_nickname_user_id != user_id:
        return
    # timeout: remove the user from game (mark inactive) and continue
    player = player_by_user_id(game, user_id)
    if player:
        player.active = False
        db_upsert_player(chat_id, player.user_id, player.username, player.nickname, player.role, player.active)
    # notify group
    await context.bot.send_message(chat_id, f"@{player.username} က nickname မပေးသေးလို့ အလိုမရှိသွားပါပြီ။")
    # advance
    game.registration_index += 1
    game.waiting_for_nickname_user_id = None
    save_game_to_db(game)
    # If too few players remain, abort
    if len(active_players(game)) < 3:
        await context.bot.send_message(chat_id, "Players fewer than 3 after timeouts. Lobby closed.")
        game.state = "ended"
        save_game_to_db(game)
        return
    # ask next
    await ask_next_nickname(context, game)


async def finish_registration(context: ContextTypes.DEFAULT_TYPE, game: Game):
    # ensure all players have nickname; default to username if missing
    for p in game.players:
        if not p.nickname:
            p.nickname = p.username
            db_upsert_player(game.chat_id, p.user_id, p.username, p.nickname, p.role, p.active)

    # assign killer
    alive_players = [p for p in game.players if p.active]
    killer_player = random.choice(alive_players)
    killer_player.role = "killer"
    game.killer_id = killer_player.user_id
    # persist roles
    for p in game.players:
        db_upsert_player(game.chat_id, p.user_id, p.username, p.nickname, p.role, p.active)
    game.state = "in_game"
    game.waiting_for_nickname_user_id = None
    game.registration_index = len(game.players)
    save_game_to_db(game)
    await context.bot.send_message(game.chat_id, "ဂိမ်းစပါပြီ")
    # send killer panel DM
    try:
        await send_killer_panel(context, killer_player.user_id, game)
    except Exception as e:
        logger.exception("Failed to send killer panel DM: %s", e)
        await context.bot.send_message(game.chat_id, "Failed to send killer control panel to killer. Ensure killer has opened DM with the bot.")


async def send_killer_panel(context: ContextTypes.DEFAULT_TYPE, killer_user_id: int, game: Game):
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Curse Others", callback_data=f"panel_curse_others:{game.chat_id}")],
            [InlineKeyboardButton("Self Curse", callback_data=f"panel_self_curse:{game.chat_id}")],
            [InlineKeyboardButton("Remove Curse", callback_data=f"panel_remove_curse:{game.chat_id}")],
            [InlineKeyboardButton("Fake Alert", callback_data=f"panel_fake_alert:{game.chat_id}")],
        ]
    )
    await context.bot.send_message(
        chat_id=killer_user_id,
        text=(
            "You are the Killer. Use the buttons below to act covertly.\n\n"
            "- Curse Others: pick a player to curse (their messages will be deleted and replaced in group)\n"
            "- Self Curse: curse yourself to bluff\n"
            "- Remove Curse: uncurse a currently cursed player\n"
            "- Fake Alert: send a 'Curse မိပြီ' message to the group without cursing anyone\n\n(Buttons will open additional choices when needed.)"
        ),
        reply_markup=kb,
    )


async def callback_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    # Panel: choose others to curse
    if data.startswith("panel_curse_others:"):
        chat_id = int(data.split(":", 1)[1])
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        if not game or game.killer_id != user.id:
            await query.answer(text="Only killer can use this.", show_alert=True)
            return
        buttons = []
        for p in game.players:
            if p.user_id == user.id or not p.active:
                continue
            buttons.append([InlineKeyboardButton(p.nickname or p.username, callback_data=f"curse:{chat_id}:{p.user_id}")])
        if not buttons:
            buttons = [[InlineKeyboardButton("No valid targets", callback_data="noop")]]
        kb = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("Cancel", callback_data="panel_cancel")]])
        await query.edit_message_text("Select player to curse:", reply_markup=kb)

    elif data.startswith("curse:"):
        _, chat_id_str, target_id_str = data.split(":")
        chat_id = int(chat_id_str)
        target_id = int(target_id_str)
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        if not game or game.killer_id != user.id:
            await query.answer(text="Only killer can do that.", show_alert=True)
            return
        target = player_by_user_id(game, target_id)
        if target and target.active:
            game.cursed.add(target_id)
            db_set_cursed(chat_id, target_id)
            save_game_to_db(game)
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Killer က တစ်ယောက်ကို နှောက်ယှက်လိုက်ပါပြီ!")
            await query.edit_message_text("Cursed.")
            logger.info("Killer %s cursed %s in chat %s", user.id, target_id, chat_id)
        else:
            await query.answer(text="Invalid target", show_alert=True)

    elif data.startswith("panel_self_curse:"):
        chat_id = int(data.split(":", 1)[1])
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        if not game or game.killer_id != user.id:
            await query.answer(text="Only killer can use this.", show_alert=True)
            return
        game.cursed.add(user.id)
        db_set_cursed(chat_id, user.id)
        save_game_to_db(game)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Killer က တစ်ယောက်ကို နှောက်ယှက်လိုက်ပါပြ���!")
        await query.edit_message_text("You cursed yourself (Self Curse).")
        logger.info("Killer %s self-cursed in chat %s", user.id, chat_id)

    elif data.startswith("panel_remove_curse:"):
        chat_id = int(data.split(":", 1)[1])
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        if not game or game.killer_id != user.id:
            await query.answer(text="Only killer can use this.", show_alert=True)
            return
        if not game.cursed:
            await query.edit_message_text("There are no cursed players currently.")
            return
        buttons = []
        for uid in list(game.cursed):
            p = player_by_user_id(game, uid)
            if not p:
                continue
            buttons.append([InlineKeyboardButton(p.nickname or p.username, callback_data=f"remove_curse:{chat_id}:{uid}")])
        buttons.append([InlineKeyboardButton("Cancel", callback_data="panel_cancel")])
        kb = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("Select cursed player to remove curse:", reply_markup=kb)

    elif data.startswith("remove_curse:"):
        _, chat_id_str, target_id_str = data.split(":")
        chat_id = int(chat_id_str)
        target_id = int(target_id_str)
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        if not game or game.killer_id != user.id:
            await query.answer(text="Only killer can use this.", show_alert=True)
            return
        if target_id in game.cursed:
            game.cursed.remove(target_id)
            db_remove_cursed(chat_id, target_id)
            save_game_to_db(game)
            await query.edit_message_text("Removed curse.")
            logger.info("Killer %s removed curse from %s in chat %s", user.id, target_id, chat_id)
        else:
            await query.answer(text="That player is not cursed.", show_alert=True)

    elif data.startswith("panel_fake_alert:"):
        chat_id = int(data.split(":", 1)[1])
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        if not game or game.killer_id != user.id:
            await query.answer(text="Only killer can use this.", show_alert=True)
            return
        await context.bot.send_message(chat_id=chat_id, text="Curse မိပြီ")
        await query.edit_message_text("Fake alert sent to group.")
        logger.info("Killer %s sent fake alert in chat %s", user.id, chat_id)

    elif data == "panel_cancel" or data == "noop":
        try:
            await query.delete_message()
        except Exception:
            await query.answer()

    elif data.startswith("vote:"):
        _, chat_id_str, target_id_str = data.split(":")
        chat_id = int(chat_id_str)
        target_id = int(target_id_str)
        game = GAMES.get(chat_id) or load_game_from_db(chat_id)
        voter_id = user.id
        vp = player_by_user_id(game, voter_id)
        if not vp or not vp.active:
            await query.answer(text="You are not an active player and cannot vote.", show_alert=True)
            return
        # check if already voted
        votes = db_get_votes(chat_id)
        if voter_id in votes:
            await query.answer(text="You already voted.", show_alert=True)
            return
        db_add_vote(chat_id, voter_id, target_id)
        await query.answer(text=f"Your vote recorded.")
        logger.info("User %s voted for %s in chat %s", voter_id, target_id, chat_id)
        # If all active players have voted, tally now
        votes = db_get_votes(chat_id)
        if len(votes) >= len(active_players(game)):
            # cancel voting timeout
            if game.voting_task and not game.voting_task.done():
                game.voting_task.cancel()
            await tally_votes(context, game)


async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    chat = message.chat
    user = message.from_user
    if chat.type not in ("group", "supergroup"):
        return
    game = GAMES.get(chat.id) or load_game_from_db(chat.id)
    if not game:
        return
    GAMES[chat.id] = game

    # registration flow: accept nickname from expected user
    if game.state == "registration" and game.waiting_for_nickname_user_id:
        if user.id == game.waiting_for_nickname_user_id:
            text = (message.text or "").strip()
            if not text:
                await message.reply_text("Nickname cannot be empty. Please send a text nickname.")
                return
            player = player_by_user_id(game, user.id)
            if player:
                player.nickname = text
                db_upsert_player(game.chat_id, player.user_id, player.username, player.nickname, player.role, player.active)
                # cancel registration timeout
                if game.registration_task and not game.registration_task.done():
                    game.registration_task.cancel()
                    game.registration_task = None
                game.registration_index += 1
                game.waiting_for_nickname_user_id = None
                save_game_to_db(game)
                await message.reply_text(f"Saved nickname: {text}")
                await ask_next_nickname(context, game)
                return
        else:
            # ignore messages from others during registration
            return

    # in-game: handle cursed deletion
    if game.state in ("in_game", "voting"):
        p = player_by_user_id(game, user.id)
        if p and p.active and user.id in game.cursed:
            nickname = p.nickname or p.username
            # schedule delete and replacement
            asyncio.create_task(handle_cursed_message(context, chat.id, message.message_id, nickname))
            return


async def handle_cursed_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, nickname: str):
    await asyncio.sleep(config.CURSE_DELETE_DELAY)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.debug("Failed to delete cursed message: %s", e)
    try:
        await context.bot.send_message(chat_id=chat_id, text=f"🤐 {nickname} စကားပြောလို့မရပါ")
    except Exception as e:
        logger.debug("Failed to send replacement message: %s", e)


# Vote command: initiate voting phase
async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("Use /vote in the group chat where the game is running.")
        return
    game = GAMES.get(chat.id) or load_game_from_db(chat.id)
    if not game:
        await update.message.reply_text("No active game in this chat.")
        return
    if game.state != "in_game":
        await update.message.reply_text("Voting can only start during the game.")
        return
    # create buttons for active players
    buttons = []
    for p in game.players:
        if p.active:
            buttons.append([InlineKeyboardButton(p.nickname or p.username, callback_data=f"vote:{chat.id}:{p.user_id}")])
    if not buttons:
        await update.message.reply_text("No active players to vote for.")
        return
    kb = InlineKeyboardMarkup(buttons)
    sent = await update.message.reply_text("Vote for who you suspect is the Killer:", reply_markup=kb)
    game.vote_message_id = sent.message_id
    game.state = "voting"
    game.vote_deadline = int(time.time()) + config.VOTE_TIMEOUT
    save_game_to_db(game)
    # schedule vote timeout
    if game.voting_task and not game.voting_task.done():
        game.voting_task.cancel()
    game.voting_task = asyncio.create_task(vote_timeout_task(context, game.chat_id))
    await update.message.reply_text(f"Voting started. You have {config.VOTE_TIMEOUT} seconds.")


async def vote_timeout_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await asyncio.sleep(config.VOTE_TIMEOUT)
    game = GAMES.get(chat_id) or load_game_from_db(chat_id)
    if not game:
        return
    if game.state != "voting":
        return
    await context.bot.send_message(chat_id, "Voting time ended. Tallying votes...")
    await tally_votes(context, game)


async def tally_votes(context: ContextTypes.DEFAULT_TYPE, game: Game):
    chat_id = game.chat_id
    votes = db_get_votes(chat_id)
    if not votes:
        await context.bot.send_message(chat_id, "No votes were cast. No one is executed.")
        # return to in_game
        game.state = "in_game"
        db_clear_votes(chat_id)
        save_game_to_db(game)
        return
    # tally counts
    tally: Dict[int, int] = {}
    for voter, target in votes.items():
        tally[target] = tally.get(target, 0) + 1
    # determine top
    top_count = max(tally.values())
    top_candidates = [uid for uid, cnt in tally.items() if cnt == top_count]
    # Tie rule: If tie, no one eliminated and Killer wins (game ends with killer victory)
    if len(top_candidates) > 1:
        # reveal killer
        killer_player = player_by_user_id(game, game.killer_id) if game.killer_id else None
        killer_nick = killer_player.nickname if killer_player else "Killer"
        await context.bot.send_message(chat_id, f"မဲတူနေမှုဖြစ်နေပါသည်။ Killer အနိုင်ရပါသည်။ Killer: {killer_nick}. ဂိမ်းပြီးပါပြီ။")
        game.state = "ended"
        db_clear_votes(chat_id)
        save_game_to_db(game)
        return

    top_user_id = top_candidates[0]
    target_player = player_by_user_id(game, top_user_id)
    if not target_player:
        await context.bot.send_message(chat_id, "Error resolving voted player.")
        game.state = "in_game"
        db_clear_votes(chat_id)
        save_game_to_db(game)
        return

    # If top is killer -> villagers win
    if target_player.role == "killer":
        await context.bot.send_message(chat_id, f"မိသွားပါပြီ! {target_player.nickname} သည် Killer ဖြစ်သည်။ ဂိမ်းပြီးပါပြီ။")
        game.state = "ended"
        db_clear_votes(chat_id)
        save_game_to_db(game)
        return
    else:
        # wrong catch: eliminate the player
        target_player.active = False
        db_upsert_player(chat_id, target_player.user_id, target_player.username, target_player.nickname, target_player.role, target_player.active)
        db_remove_cursed(chat_id, target_player.user_id)
        await context.bot.send_message(chat_id, f"မှားယွင်းဖမ်းဆီးမိသည်။ {target_player.nickname} သည် ဂိမ်းမှ ထွက်ရမည်။")
        db_clear_votes(chat_id)
        save_game_to_db(game)
        # Check win condition: if villagers count equals killers -> killer wins
        villagers = active_villagers_count(game)
        killers = active_killers_count(game)
        if killers >= villagers:
            killer_player = player_by_user_id(game, game.killer_id) if game.killer_id else None
            killer_nick = killer_player.nickname if killer_player else "Killer"
            await context.bot.send_message(chat_id, f"Killer အနိုင်ရပါပြီ။ Killer: {killer_nick}. ဂိမ်းပြီးပါပြီ။")
            game.state = "ended"
            save_game_to_db(game)
            return
        # otherwise continue game
        game.state = "in_game"
        save_game_to_db(game)
        return


# ---------- Startup / helpers ----------
async def on_startup(application: Application):
    logger.info("Bot starting up.")
    init_db()
    # Load incomplete games into memory
    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT chat_id FROM games WHERE state IN ('lobby','registration','in_game','voting')")
    rows = cur.fetchall()
    con.close()
    for (chat_id,) in rows:
        g = load_game_from_db(chat_id)
        if g:
            GAMES[chat_id] = g
            logger.info("Loaded game from DB for chat %s state=%s", chat_id, g.state)
            # If a game was in voting state and the vote_deadline has passed, tally immediately
            if g.state == "voting":
                if g.vote_deadline and int(time.time()) >= g.vote_deadline:
                    # schedule immediate tally
                    asyncio.create_task(tally_votes(application.bot, g))
                else:
                    # schedule remaining vote timeout
                    remaining = (g.vote_deadline or 0) - int(time.time())
                    if remaining > 0:
                        g.voting_task = asyncio.create_task(vote_timeout_task(application, chat_id))
            # If registration waiting, schedule remaining registration timeout
            if g.state == "registration" and g.waiting_for_nickname_user_id:
                # schedule fresh timeout (we don't have per-player time left persisted), using full timeout
                g.registration_task = asyncio.create_task(registration_timeout(application, chat_id, g.waiting_for_nickname_user_id))


def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("Please set TELEGRAM_TOKEN environment variable.")
        return
    application = Application.builder().token(token).build()

    # Handlers
    application.add_handler(CommandHandler("start_game", start_game_cmd))
    application.add_handler(CommandHandler("vote", vote_command))
    application.add_handler(CallbackQueryHandler(join_or_start_callback, pattern="^(join|start_game)$"))
    application.add_handler(CallbackQueryHandler(callback_dispatcher, pattern="^"))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, group_message_handler))

    application.post_init = on_startup

    logger.info("Running bot (polling)...")
    application.run_polling()


if __name__ == "__main__":
    main()

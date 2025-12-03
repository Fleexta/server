#  Copyright (c) 2025 Timofei Kirsanov

import sqlite3

import images
from data.tables import Account, Message
from exceptions import Error


def db(edit: bool = False):
    def decorator(func):
        def wrapper(*args):
            con = sqlite3.connect("db.sql")
            cur = con.cursor()
            try:
                f = func(*args, cur)
            except IndexError:
                raise Error.NOT_FOUND
            if edit:
                con.commit()
            con.close()
            return f
        return wrapper
    return decorator


@db()
def get_user(login, cur):
    array = cur.execute(f"""SELECT * FROM Accounts
    WHERE username = ?""", (login, )).fetchall()
    if len(array) == 0:
        return -1
    else:
        return Account.generate(array[0])


@db()
def get_user_by_id(id, cur):
    array = cur.execute(f"""SELECT * FROM Accounts
    WHERE id = ?""", (id, )).fetchall()
    if len(array) == 0:
        return -1
    else:
        return Account.generate(array[0])


@db()
def get_all_users(cur):
    users = cur.execute("SELECT * FROM Accounts").fetchall()
    result = {}
    for user in users:
        user_form = Account.generate(user)
        chats = {}
        for chat in user_form.chats:
            chats[get_chat_name(chat)] = chat
        result[user_form.username] = {
            "id": user_form.id,
            "username": user_form.username,
            "hashed_password": user_form.hashed_password,
            "chats": chats,
            "email": user_form.email,
            "profile": user_form.profile,
        }
    return result


@db()
def get_messages(chat, cur):
    messages = cur.execute("""
    SELECT * FROM Messages
    WHERE chat = ?""", (chat, )).fetchall()
    result = []
    for message in messages:
        message_form = Message.generate(message)
        result.append({
            "id": message_form.id,
            "time": message_form.time,
            "author": message_form.author,
            "message": message_form.message,
            "media": message_form.media,
            "chat": message_form.chat,
        })
    return result


@db()
def get_message(chat, id, cur):
    message = cur.execute("""
    SELECT * FROM Messages
    WHERE chat = ? AND id = ?""", (chat, id)).fetchall()[0]
    message_form = Message.generate(message)
    return {
        "id": message_form.id,
        "time": message_form.time,
        "author": message_form.author,
        "message": message_form.message,
        "media": message_form.media,
        "chat": message_form.chat,
    }


@db(True)
def edit_message(chat, id, message, cur):
    cur.execute("""
    UPDATE Messages
    SET message = ?
    WHERE chat = ? AND id = ?""", (message, chat, id))


@db(True)
def delete_message(chat, id, cur):
    cur.execute("""
    DELETE FROM Messages
    WHERE chat = ? AND id = ?""", (chat, id))


@db(True)
def create_user(username, password, id, cur):
    avatar = images.generate_avatar(username)
    cur.execute("""
    INSERT INTO Profiles (avatar) VALUES (?)""", (avatar, )).fetchall()
    profile = cur.execute("""
    SELECT id FROM Profiles ORDER BY id DESC LIMIT 1;
    """).fetchall()[0][0]
    cur.execute("""
    INSERT INTO Accounts (username, hashed_password, id, profile) VALUES
    (?, ?, ?, ?)""", (username, password, id, profile))


@db(True)
def create_chat(name, id, time, member, cur):
    cur.execute("""
    INSERT INTO Chats (name, id, time, members) VALUES (?, ?, ?, ?)""", (name, id, time, member))


@db(True)
def send_message(id, time, author, chat, message, cur):
    cur.execute("""
    INSERT INTO Messages (id, time, author, message, chat) VALUES (?, ?, ?, ?, ?)""",
                (id, time, author, message, chat))


@db(True)
def send_media_message(id, time, author, chat, message, media, cur):
    cur.execute("""
    INSERT INTO Messages (id, time, author, message, media, chat) VALUES (?, ?, ?, ?, ?, ?)""",
                (id, time, author, message, media, chat))


@db()
def is_available_id(table, id, cur):
    result = cur.execute(f"""
    SELECT id FROM {table}
    WHERE id = {id}""").fetchall()
    if not result:
        return True
    else:
        return False


@db()
def get_chat_name(id, cur):
    return cur.execute(f"""
    SELECT name FROM Chats
    WHERE id = ?""", (id, )).fetchall()[0][0]


@db()
def get_user_avatar(id, cur):
    return cur.execute("""
    SELECT avatar FROM Profiles
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id = ?)""", (id, )).fetchall()[0][0]


@db(True)
def set_user_avatar(avatar, id, cur):
    cur.execute("""
    UPDATE Profiles
    SET avatar = ?
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id = ?)""", (avatar, id))


@db()
def get_user_about(id, cur):
    return cur.execute("""
    SELECT about FROM Profiles
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id = ?)""", (id, )).fetchall()[0][0]


@db()
def get_username(id, cur):
    return cur.execute("""
    SELECT username FROM Accounts
    WHERE id = ?""", (id, )).fetchall()[0][0]


@db()
def get_name(id, cur):
    return cur.execute("""
    SELECT name FROM Profiles
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id = ?)""", (id, )).fetchall()[0][0]


@db()
def get_chat_avatar(id, cur):
    return cur.execute("""
    SELECT avatar FROM Chats
    WHERE id = ?""", (id, )).fetchall()[0][0]


@db(True)
def set_chat_avatar(avatar, id, cur):
    cur.execute("""
    UPDATE Chats
    SET avatar = ?
    WHERE id = ?""", (avatar, id))


@db()
def get_chat_members(id, cur):
    members = cur.execute("""
    SELECT members FROM Chats
    WHERE id = ?""", (id, )).fetchall()[0][0]
    return list(map(int, members.split(",")))


@db(True)
def add_chat(id, chat, cur):
    chats = cur.execute("""
    SELECT chats FROM Accounts
    WHERE id = ?""", (id, )).fetchall()[0][0]
    if chats is None:
        cur.execute("""
        UPDATE Accounts
        SET chats = ?
        WHERE id = ?""", (str(chat), id))
    else:
        cur.execute("""
        UPDATE Accounts
        SET chats = ?
        WHERE id = ?""", (chats + "," + str(chat), id))


@db()
def get_chat(id, cur):
    array = cur.execute(f"""SELECT * FROM Chats
    WHERE id = ?""", (id, )).fetchall()
    if len(array) == 0:
        return -1
    else:
        return array[0]


@db(True)
def put_media(id, cur):
    return cur.execute("""
    SELECT avatar FROM Profiles
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id = ?)""", (id, )).fetchall()[0][0]


@db(True)
def add_user_to_chat(user_id, chat_id, cur):
    members = cur.execute("""
    SELECT members FROM Chats
    WHERE id = ?""", (chat_id, )).fetchall()[0][0]
    cur.execute("""
    UPDATE Chats
    SET members = ?
    WHERE id = ?""", (members + "," + str(user_id), chat_id))


@db()
def get_media(key, cur):
    return cur.execute("""
    SELECT name, value FROM Media
    WHERE id = ?""", (key, )).fetchall()[0]


@db()
def get_chat_from_invite(key, cur):
    return cur.execute("""
    SELECT value FROM Invites
    WHERE id = ?""", (key, )).fetchall()[0][0]


@db()
def get_chat_invite(chat, cur):
    invite = cur.execute("""
    SELECT invite FROM Chats
    WHERE id = ?""", (chat, )).fetchall()[0][0]
    if invite is None:
        return -1
    else:
        return invite


@db(True)
def upload_media(id, name, media, cur):
    cur.execute("""
    INSERT INTO Media (id, name, value) VALUES (?, ?, ?)""", (id, name, media))


@db(True)
def upload_invite(id, name, value, cur):
    cur.execute("""
    INSERT INTO Invites (id, name, value) VALUES (?, ?, ?)""", (id, name, value))


@db(True)
def update_invites_from_chat(chat, invite, cur):
    cur.execute("""
    UPDATE Chats
    SET invite = ?
    WHERE id = ?""", (invite, chat))


@db(True)
def update_username(id, username, cur):
    cur.execute("""
    UPDATE Accounts
    SET username = ?
    WHERE id = ?""", (username, id))


@db(True)
def update_email(id, email, cur):
    cur.execute("""
    UPDATE Accounts
    SET email = ?
    WHERE id = ?""", (email, id))


@db(True)
def update_about(id, about, cur):
    cur.execute("""
    UPDATE Profile
    SET about = ?
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id ?)""", (about, id))


@db(True)
def update_name(id, name, cur):
    cur.execute("""
    UPDATE Profile
    SET name = ?
    WHERE id = (
    SELECT profile FROM Accounts
    WHERE id ?)""", (name, id))

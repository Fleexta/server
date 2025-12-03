#  Copyright (c) 2025 Timofei Kirsanov
import asyncio
import io
import json
import mimetypes
import random
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Iterable

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import StreamingResponse

import data.database
import classes
from data import auth, database
from exceptions import Error
from hashes import HashManager

app = FastAPI(
    title="Fleexta server",
    description="Server API for Fleexta",
    version="0.5.2"
)

STREAM_DELAY = 1
RETRY_TIMEOUT = 15000


def check(user_id, chat_id):
    members = database.get_chat_members(chat_id)
    return user_id in members


def create_chat(name: str, types: str, member: str):
    current_datetime = datetime.now().isoformat()
    id = random.randint(1000000000, 9999999999)
    if types == "chat":
        if database.is_available_id("Chats", id):
            database.create_chat(name, id, current_datetime, member)
            database.add_chat(member, id)
            return id
        else:
            create_chat(name, types, member)
    elif types == "channel":
        if database.is_available_id("Chats", -id):
            database.create_chat(name, id, current_datetime, member)
            database.add_chat(member, id)
            return id
        else:
            create_chat(name, types, member)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Types is wrong")


def get_new_messages(chat) -> Iterable:
    chat_id = uuid.uuid4()
    return [
        {
            "event": f"chat-{chat}",
            "retry": RETRY_TIMEOUT,
            "data": json.dumps(
                database.get_messages(chat)
            ),
            "id": str(chat_id),
        }
    ]


async def event_generator(request: Request, chat):
    while True:
        if await request.is_disconnected():
            break
        for message in get_new_messages(chat):
            yield message
        await asyncio.sleep(STREAM_DELAY)


@app.get("/c/{chat}")
async def message_stream(
        request: Request,
        current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
        chat: str
):
    if database.get_chat(int(chat)) == -1 and len(chat) == 10:
        raise Error.CHAT_NOT_FOUND
    if database.get_chat(int(chat)) == -1 and len(chat) == 8:
        name = current_user.username + " , " + str(database.get_user_by_id(int(chat)).username)
        chat_id = create_chat(name, "chat", str(current_user.id))
        database.add_chat(int(chat), chat_id)
        database.add_user_to_chat(int(chat), chat_id)
        auth.refresh_db()
        return {"id": chat_id}
    if not check(current_user.id, chat):
        raise Error.CHAT_FORBIDDEN
    return EventSourceResponse(event_generator(request, chat))


@app.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> classes.Token:
    user = auth.authenticate_user(auth.users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return classes.Token(access_token=access_token, token_type="bearer", id=user.id)


@app.post("/reg")
async def register_account(
        # form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        form_data: classes.RegistrationForm
):
    if data.database.get_user(form_data.username) == -1:
        auth.create_user(form_data.username, form_data.password, form_data.name)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Change login")
    return {"registration": "ok", "login": form_data.username}


@app.get("/me", response_model=classes.User)
async def read_me(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
):
    return current_user


@app.get("/chats")
async def get_my_chats(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
):
    return current_user.chats


@app.post("/c/{dest}/send")
async def send(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    msg: classes.Msg,
    dest: int
):
    if not check(current_user.id, dest):
        raise Error.CHAT_FORBIDDEN
    current_datetime = datetime.now().isoformat()
    messages = database.get_messages(dest)
    if len(messages) == 0:
        id = 1
    else:
        id = messages[-1]["id"] + 1
    if msg.media is None:
        database.send_message(id, current_datetime, current_user.id, dest, msg.message)
    else:
        database.send_media_message(id, current_datetime, current_user.id, dest, msg.message, msg.media)
    return {current_user.username: msg.message}


@app.post("/create")
async def create(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    chat: classes.Chat
):
    create_chat(chat.name, chat.types, str(current_user.id))
    auth.refresh_db()
    return {chat.name: id}


@app.get("/c/{chat}/{id}")
async def get_message(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    chat: int,
    id: int
):
    if not check(current_user.id, chat):
        raise Error.CHAT_FORBIDDEN
    return database.get_message(chat, id)


@app.post("/c/{chat}/{id}/edit")
async def edit_message(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    chat: int,
    id: int,
    msg: classes.Msg
):
    if not check(current_user.id, chat):
        raise Error.CHAT_FORBIDDEN
    message = database.get_message(chat, id)
    if message["author"] != current_user.id:
        raise Error.ACTION_FORBIDDEN
    database.edit_message(chat, id, msg.message)
    message = database.get_message(chat, id)
    return {message["id"]: message["message"]}


@app.post("/c/{chat}/{id}/delete")
async def delete_message(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    chat: int,
    id: int
):
    if not check(current_user.id, chat):
        raise Error.CHAT_FORBIDDEN
    message = database.get_message(chat, id)
    if message["author"] != current_user.id:
        raise Error.ACTION_FORBIDDEN
    database.delete_message(chat, id)
    return {message["id"]: message["message"]}


@app.get("/media/{hash}")
async def get_media(
    hash: str
):
    result = database.get_media(hash)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    filename, _ = result

    return filename


@app.get("/download/{hash}")
async def get_media(
    hash: str
):
    result = database.get_media(hash)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    filename, blob_data = result

    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    mem_file = io.BytesIO(blob_data)
    response = StreamingResponse(mem_file, media_type=mime_type)
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Content-Length"] = str(len(blob_data))

    return response


@app.get("/")
async def invite_from_link(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    invite: str
):
    chat_id = database.get_chat_from_invite(invite)
    database.add_chat(current_user.id, chat_id)
    database.add_user_to_chat(current_user.id, chat_id)
    auth.refresh_db()
    return


@app.post("/upload/media")
async def upload_media(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    file: UploadFile
):
    contents = await file.read()
    hash = HashManager().hash
    database.upload_media(hash, file.filename, contents)
    return {"upload": hash}


@app.post("/generate/invite/{dest}/{data}")
async def generate_invite(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    dest: str,
    data: int
):
    if dest != "chat" and dest != "call":
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
    hash = HashManager().hash
    database.upload_invite(hash, dest, data)
    if dest == "chat":
        database.update_invites_from_chat(data, hash)
    return {"generate": hash}


@app.post("/media/edit/{dest}")
async def edit_media(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    dest: str,
    file: UploadFile
):
    contents = await file.read()
    if dest == "avatar":
        database.set_user_avatar(contents, current_user.id)
        return {current_user.id: "ok"}
    else:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


@app.post("/account/edit/{dest}")
async def edit_account(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    user_data: classes.UserData
):
    if not (user_data.name is None):
        database.update_name(current_user.id, user_data.name)
    if not (user_data.about is None):
        database.update_about(current_user.id, user_data.name)
    if not (user_data.email is None):
        database.update_email(current_user.id, user_data.email)
    if not (user_data.username is None):
        database.update_username(current_user.id, user_data.username)


@app.get("/search/{username}")
async def search_users(
    current_user: Annotated[classes.User, Depends(auth.get_current_active_user)],
    username: str
):
    user = database.get_user(username)
    return {"id": user.id, "username": user.username}


@app.get("/get/{root}/{dest}/{data}")
async def get_resource(
    root: str,
    dest: str,
    data: str
):
    if root == "user":
        id = int(data)
        match dest:
            case "avatar":
                img_data = database.get_user_avatar(id)
                image_stream = io.BytesIO(img_data)
                return StreamingResponse(image_stream, media_type="image/png")
            case "username":
                return {id: "@" + database.get_username(id)}
            case "name":
                return {id: database.get_name(id)}
            case "about":
                return {id: database.get_user_about(id)}
    elif root == "chat":
        id = int(data)
        match dest:
            case "avatar":
                img_data = database.get_chat_avatar(id)
                image_stream = io.BytesIO(img_data)
                return StreamingResponse(image_stream, media_type="image/png")
            case "name":
                return {id: database.get_chat_name(id)}
            case "members":
                return {id: database.get_chat_members(id)}
            case "invite":
                return {id: database.get_chat_invite(id)}
    else:
        raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8001)

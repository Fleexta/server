from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    id: int


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    id: int
    chats: dict
    email: str | None = None
    profile: int | None = None
    disabled: bool | None = None


class UserData(BaseModel):
    username: str
    name: str
    about: str
    email: str


class Chat(BaseModel):
    name: str
    types: str


class Msg(BaseModel):
    message: str = None
    media: str = None


class UserInDB(User):
    hashed_password: str

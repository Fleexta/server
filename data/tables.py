#  Copyright (c) 2025 Timofei Kirsanov

class Account:
    def __init__(self,
                 id: int, username: str, hashed_password: str, chats: list, email: str, profile: int):
        self.id = id
        self.username = username
        self.hashed_password = hashed_password
        self.chats = chats
        self.email = email
        self.profile = profile

    def __str__(self):
        return (f"id: {self.id}\nusername: {self.username}\n"
                f"hashed_password: {self.hashed_password}\nchats: {self.chats}\nemail: "
                f"{self.email}\nprofile: {self.profile}")

    @staticmethod
    def generate(array):
        if array[3]:
            chats = list(map(int, array[3].split(",")))
        else:
            chats = []
        return Account(array[0], array[1], array[2], chats, array[4], array[5])


class Message:
    def __init__(self, id: int, time: str, author: int, message: str, media: str, chat: int):
        self.id = id
        self.time = time
        self.author = author
        self.message = message
        self.media = media
        self.chat = chat

    def __str__(self):
        return (f"id: {self.id}\ntime: {self.time}\nauthor: {self.author}\n"
                f"message: {self.message}\nmedia: {self.media}\nchat: {self.chat}")

    @staticmethod
    def generate(array):
        return Message(array[0], array[1], array[2], array[3], array[4], array[5])

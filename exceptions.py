from fastapi import HTTPException
from starlette import status


class Error:
    CHAT_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    CHAT_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to the chat")
    ACTION_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot perform this action")
    FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

import uuid;

from fastapi import FastAPI, APIRouter;
from fastapi import UploadFile;
from fastapi.responses import FileResponse

from authenticate import *;
from InfoGrep_BackendSDK import parse_api
import ChatroomDBAPIs

import requests

router = APIRouter(prefix='/api', tags=["api"]);
chatroomdb = ChatroomDBAPIs.ChatroomDB();


"""Creates a chatroom for the user"""
@router.post('/room')
def post_room(user_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie)
    chatroom_uuid = uuid.uuid4();
    chatroomdb.createChatroom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)
    return {"detail": chatroom_uuid}

"""Deletes the specified chatroom if the user is authorized to do so"""
@router.delete('/room')
def delete_room(user_uuid, chatroom_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie)
    chatroomdb.deleteChatroom(chatroom_uuid=chatroom_uuid)
    return {"detail": "Chatroom " + chatroom_uuid + " has been deleted"}

"""Get all the messge uuids in a chatroom."""
@router.get('/room')
def get_room(user_uuid, chatroom_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie)
    messages = chatroomdb.getMessages(chatroom_uuid=chatroom_uuid)
    return messages

"""Update chatroom name or roles."""
@router.put('/room')
def put_room(user_uuid, chatroom_uuid, fields, cookie):
    raise HTTPException(status_code=501, detail='function not implemented')


"""Gets all the chatrooms a user is in"""
@router.get('/rooms')
def get_rooms(user_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie);
    chatroomlist = chatroomdb.getChatrooms(user_uuid)
    return chatroomlist


"""Returns the message associated with a message uuid"""
@router.get('/message')
def get_message(user_uuid, chatroom_uuid, message_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie);
    message = chatroomdb.getMessage(chatroom_uuid=chatroom_uuid, message_uuid=message_uuid);
    return message

"""Enables the user to send a message in a chatroom"""
@router.post('/message')
def post_message(user_uuid, chatroom_uuid, message, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie);
    message_uuid = uuid.uuid4();
    chatroomdb.createMessage(user_uuid=user_uuid, chatroom_uuid=chatroom_uuid, message_uuid=message_uuid, message=message);
    return


"""Deletes a message in a chatroom"""
@router.delete('/message')
def delete_message(user_uuid, chatroom_uuid, message_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie);
    chatroomdb.deleteMessage(chatroom_uuid=chatroom_uuid, message_uuid=message_uuid);
    return

"""Deletes all messages in a chatroom"""
@router.delete('/messages')
def delete_messages(user_uuid, chatroom_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie);
    chatroomdb.deleteMessage(chatroom_uuid=chatroom_uuid);
    return

"""This endpoint should be the chatroom authentication endpoint. This should validate if a user is in the room"""
@router.get('/userinroom')
def get_userinroom(user_uuid, chatroom_uuid, cookie):
    #auth_user(user_uuid=user_uuid, cookie=cookie)
    return {"detail": chatroomdb.existsChatroom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)};

"""We need to come up with a way for the user to receive messages that have been sent. 
We can send messages and get messages that we know the uuid for.
What we need to do now is a come up with a way to tell clients that a message has been sent."""

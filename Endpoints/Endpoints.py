import uuid;

from fastapi import FastAPI, APIRouter;
from fastapi import UploadFile;
from fastapi.responses import FileResponse

from authenticate import *;
from InfoGrep_BackendSDK import parse_api
from InfoGrep_BackendSDK import authentication_sdk
from InfoGrep_BackendSDK import fms_api
from InfoGrep_BackendSDK import ai_sdk
import ChatroomDBAPIs

router = APIRouter(prefix='/api', tags=["api"]);
chatroomdb = ChatroomDBAPIs.ChatroomDB();

"""This endpoint should be the chatroom authentication endpoint. This should validate if a user is in the room"""
@router.get('/userinroom')
def get_userinroom(chatroom_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    return {"detail": chatroomdb.userInRoom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)};


"""Creates a chatroom for the user"""
@router.post('/room')
def post_room(cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    chatroom_uuid = uuid.uuid4();
    chatroomdb.createChatroom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)
    return {"detail": chatroom_uuid}

"""Deletes the specified chatroom if the user is authorized to do so"""
@router.delete('/room')
def delete_room(chatroom_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    filelist = fms_api.fms_getFileList(chatroom_uuid=chatroom_uuid, cookie=cookie).json()['list']
    for file in filelist:
        print(file['File_UUID'])
        fms_api.fms_deleteFile(chatroom_uuid=chatroom_uuid, file_uuid=file['File_UUID'], cookie=cookie)
    chatroomdb.deleteChatroom(chatroom_uuid=chatroom_uuid)
    return {"detail": "Chatroom " + chatroom_uuid + " has been deleted"}

"""Get all the messge uuids in a chatroom."""
@router.get('/room')
def get_room(chatroom_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    messages = chatroomdb.getMessages(chatroom_uuid=chatroom_uuid)
    messagejson = {'list': []}
    for item in messages:
        messagejson['list'].append({'User_UUID': item[0], 'TimeStamp': item[1], 'Message_UUID': item[2]})
    return messagejson

"""Update chatroom name or roles."""
@router.put('/room')
def put_room(chatroom_uuid, fields, cookie):
    raise HTTPException(status_code=501, detail='function not implemented')


"""Gets all the chatrooms a user is in"""
@router.get('/rooms')
def get_rooms(cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    chatroomlist = chatroomdb.getChatrooms(user_uuid)
    return chatroomlist


"""Returns the message associated with a message uuid"""
@router.get('/message')
def get_message(chatroom_uuid, message_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    message = chatroomdb.getMessage(chatroom_uuid=chatroom_uuid, message_uuid=message_uuid);
    return message

"""Enables the user to send a message in a chatroom"""
@router.post('/message')
def post_message(chatroom_uuid, message, cookie):
    user_uuid = ''
    if cookie == 'infogrep-chatbot-summary':
        user_uuid = '00000000-0000-0000-0000-000000000000'
    else:
        user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    message_uuid = uuid.uuid4();
    chatroomdb.createMessage(user_uuid=user_uuid, chatroom_uuid=chatroom_uuid, message_uuid=message_uuid, message=message);

    #do not generate infogrep-responses to infogrep-responses.
    if user_uuid !=  '00000000-0000-0000-0000-000000000000':
        ai_sdk.get_Response(chatroom_uuid=chatroom_uuid, message=message, cookie=cookie)
    return


"""Deletes a message in a chatroom"""
@router.delete('/message')
def delete_message(chatroom_uuid, message_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    chatroomdb.deleteMessage(chatroom_uuid=chatroom_uuid, message_uuid=message_uuid);
    return

"""Deletes all messages in a chatroom"""
@router.delete('/messages')
def delete_messages(chatroom_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie).profile()["user_uuid"]
    chatroomdb.deleteMessage(chatroom_uuid=chatroom_uuid);
    return


"""We need to come up with a way for the user to receive messages that have been sent. 
We can send messages and get messages that we know the uuid for.
What we need to do now is a come up with a way to tell clients that a message has been sent."""

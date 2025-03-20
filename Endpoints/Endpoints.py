import uuid;

from fastapi import FastAPI, APIRouter, Request
from fastapi import UploadFile;
from fastapi.responses import FileResponse
from fastapi.openapi.docs import get_swagger_ui_html

from authenticate import *;
from InfoGrep_BackendSDK import authentication_sdk
from InfoGrep_BackendSDK import fms_api
from InfoGrep_BackendSDK import ai_sdk
import ChatroomDBAPIs

router = APIRouter(prefix='/api', tags=["api"]);
chatroomdb = ChatroomDBAPIs.ChatroomDB();

CHATBOT_UUID = '00000000-0000-0000-0000-000000000000'
"""This endpoint should be the chatroom authentication endpoint. This should validate if a user is in the room"""
@router.get('/userinroom')
def get_userinroom(request: Request, chatroom_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    return {"detail": chatroomdb.userInRoom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)};


def internal_verify_user_in_chatroom(request: Request, chatroom_uuid, cookie):
    user_in_room = get_userinroom(request=request, chatroom_uuid=chatroom_uuid, cookie=cookie);
    if user_in_room["detail"] == False:
         raise HTTPException(status_code= 401, detail="User not in room")

"""Creates a chatroom for the user"""
@router.post('/room')
def post_room(request: Request, cookie, embedding_model, chat_model, provider, chatroom_name="New Chatroom"):
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    chatroom_uuid = uuid.uuid4()
    chatroomdb.createChatroom(chatroom_uuid=chatroom_uuid, chatroom_name=chatroom_name, user_uuid=user_uuid, embedding_model=embedding_model, chat_model=chat_model, provider=provider)
    return {"id": chatroom_uuid, "name": chatroom_name}

"""Deletes the specified chatroom if the user is authorized to do so"""
@router.delete('/room')
def delete_room(request: Request, chatroom_uuid, cookie):
    authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    filelist = fms_api.fms_getFileList(chatroom_uuid=chatroom_uuid, cookie=cookie).json()['list']
    for file in filelist:
        print(file['File_UUID'])
        fms_api.fms_deleteFile(chatroom_uuid=chatroom_uuid, file_uuid=file['File_UUID'], cookie=cookie)
    chatroomdb.deleteChatroom(chatroom_uuid=chatroom_uuid)
    return {"detail": "Chatroom " + chatroom_uuid + " has been deleted"}

"""Get all the messge uuids in a chatroom."""
@router.get('/room')
def get_room(request: Request, chatroom_uuid, cookie):
    authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    messages = chatroomdb.getMessages(chatroom_uuid=chatroom_uuid)
    embedding_model = chatroomdb.getChatroomEmbeddingModel(chatroom_uuid=chatroom_uuid)
    chat_model = chatroomdb.getChatroomChatModel(chatroom_uuid=chatroom_uuid)
    provider = chatroomdb.getChatroomModelProvider(chatroom_uuid=chatroom_uuid)
    result = {'list': [], 'embedding_model': embedding_model, 'chat_model': chat_model, 'provider': provider}
    for item in messages:
        result['list'].append({'User_UUID': item[0], 'TimeStamp': item[1], 'Message_UUID': item[2], 'Message': item[3], 'References': item[4]})
    return result

"""Update chatroom name or roles."""
@router.put('/room')
def put_room(request: Request, chatroom_uuid, fields, cookie):
    raise HTTPException(status_code=501, detail='function not implemented')

"""Updates the name for a chatroom"""
@router.put('/roomname')
def put_chatroom_name(request: Request, chatroom_uuid, new_name, cookie):
    internal_verify_user_in_chatroom(request=request, chatroom_uuid=chatroom_uuid, cookie=cookie);
    chatroomdb.updateRoomName(chatroom_uuid=chatroom_uuid, chatroom_name=new_name);

@router.put('/roommodel')
def change_chatroom_llm(request: Request, chatroom_uuid, new_model_provider, new_model, cookie):
    internal_verify_user_in_chatroom(request=request, chatroom_uuid=chatroom_uuid, cookie=cookie);
    chatroomdb.updateLLM(chatroom_uuid=chatroom_uuid, chatroom_model=new_model, model_provider=new_model_provider);

"""Gets all the chatrooms a user is in"""
@router.get('/rooms')
def get_rooms(request: Request, cookie):
    user_uuid = authentication_sdk.User(cookie, request.headers).profile()["user_uuid"]
    chatroomlist = chatroomdb.getChatrooms(user_uuid)
    chatroomjson = {'list': []}
    for item in chatroomlist:
        chatroomjson['list'].append({'CHATROOM_UUID': item[0], 'CHATROOM_NAME': item[1]})
    return chatroomjson


"""Returns the message associated with a message uuid"""
@router.get('/message')
def get_message(request: Request, chatroom_uuid, message_uuid, cookie):
    authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    message = chatroomdb.getMessage(chatroom_uuid=chatroom_uuid, message_uuid=message_uuid);
    return message

"""Enables the user to send a message in a chatroom"""
@router.post('/message')
def post_message(request: Request, chatroom_uuid, message, cookie):
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    chatroomdb.createMessage(user_uuid=user_uuid, chatroom_uuid=chatroom_uuid, message_uuid=uuid.uuid4(), message=message, reference='');
    # Fetch chatroom settings
    embedding_model = chatroomdb.getChatroomEmbeddingModel(chatroom_uuid=chatroom_uuid)
    chat_model = chatroomdb.getChatroomChatModel(chatroom_uuid=chatroom_uuid)
    provider = chatroomdb.getChatroomModelProvider(chatroom_uuid=chatroom_uuid)
    messages = chatroomdb.getMessages(chatroom_uuid=chatroom_uuid)
    # Get a response from AI service
    history = [{'is_user': m[0] != CHATBOT_UUID, 'message': m[3]} for m in messages]
    response = ai_sdk.get_Response(history=history, chatroom_uuid=chatroom_uuid, message=message, sessionToken=cookie, headers=request.headers, embedding_model=embedding_model, chat_model=chat_model, provider=provider)
    chatroomdb.createMessage(user_uuid=CHATBOT_UUID, chatroom_uuid=chatroom_uuid, message_uuid=uuid.uuid4(), message=response['data']['response'], reference=response['data']['citations'])


"""Deletes a message in a chatroom"""
@router.delete('/message')
def delete_message(request: Request, chatroom_uuid, message_uuid, cookie):
    authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    chatroomdb.deleteMessage(chatroom_uuid=chatroom_uuid, message_uuid=message_uuid);
    return

"""Deletes all messages in a chatroom"""
@router.delete('/messages')
def delete_messages(request: Request, chatroom_uuid, cookie):
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    chatroomdb.deleteMessages(chatroom_uuid=chatroom_uuid);
    return

@router.get("/docs")
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/chatroom/openapi.json",
        title="Chatroom API Doc"
    )
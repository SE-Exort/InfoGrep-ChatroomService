
from fastapi import Body, APIRouter, HTTPException, Request
from fastapi.params import Depends
from fastapi.openapi.docs import get_swagger_ui_html
import requests

from InfoGrep_BackendSDK import authentication_sdk
from InfoGrep_BackendSDK import fms_api
from InfoGrep_BackendSDK import ai_sdk
from db import ChatroomIntegrations, ChatroomMessages, ChatroomRole, ChatroomRoles, ChatroomWebhookType, ChatroomWebhooks, Chatrooms, get_db
from sqlalchemy.orm import Session
from pydantic import BaseModel

router = APIRouter(prefix='/api', tags=["api"])

CHATBOT_UUID = '00000000-0000-0000-0000-000000000000'

def check_user_in_chatroom(chatroom_uuid: str, user_uuid: str, db: Session) -> bool:
    exists_query = db.query(ChatroomRoles).where(ChatroomRoles.chatroom_uuid==chatroom_uuid).where(ChatroomRoles.user_uuid==user_uuid).exists()
    return db.query(exists_query).scalar()

def ensure_user_in_chatroom(request: Request, chatroom_uuid: str, cookie: str, db: Session):
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()['user_uuid']
    if not check_user_in_chatroom(chatroom_uuid, user_uuid, db):
         raise HTTPException(status_code= 401, detail="User not in room")
    
"""This endpoint should be the chatroom authentication endpoint. This should validate if a user is in the room"""
@router.get('/userinroom')
def get_userinroom(request: Request, chatroom_uuid, cookie, db: Session = Depends(get_db)):
    user = authentication_sdk.User(cookie, headers=request.headers)
    return {"detail": check_user_in_chatroom(chatroom_uuid, user.profile()['user_uuid'], db)}

"""Creates a chatroom for the user"""
@router.post('/room')
def post_room(request: Request, cookie, embedding_model, chat_model, chat_provider, embedding_provider, chatroom_name="New Chatroom", db: Session = Depends(get_db)):
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    new_chatroom = Chatrooms(name=chatroom_name,
                     embedding_model=embedding_model,
                     chat_model=chat_model,
                     chat_provider=chat_provider,
                     embedding_provider=embedding_provider)
    db.add(new_chatroom)
    db.commit()

    # Add user to chatroom
    user_role = ChatroomRoles(user_uuid=user_uuid, chatroom_uuid=new_chatroom.id, role=ChatroomRole.Owner)
    db.add(user_role)
    db.commit()
    return new_chatroom

"""Deletes the specified chatroom if the user is authorized to do so"""
@router.delete('/room')
def delete_room(request: Request, chatroom_uuid, cookie, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    filelist = fms_api.fms_getFileList(chatroom_uuid=chatroom_uuid, cookie=cookie).json()['list']
    for file in filelist:
        print(file['File_UUID'])
        fms_api.fms_deleteFile(chatroom_uuid=chatroom_uuid, file_uuid=file['File_UUID'], cookie=cookie)
    db.query(Chatrooms).where(Chatrooms.id==chatroom_uuid).delete()
    db.commit()
    return {"detail": "Chatroom " + chatroom_uuid + " has been deleted"}

"""Get the full chatroom including its messages."""
@router.get('/room')
def get_room(request: Request, chatroom_uuid, cookie, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    chatroom = db.query(Chatrooms).where(Chatrooms.id==chatroom_uuid).one()
    chatroom_messages = db.query(ChatroomMessages).order_by(ChatroomMessages.timestamp).where(ChatroomMessages.chatroom_uuid==chatroom.id).all()
    integrations = db.query(ChatroomIntegrations).where(ChatroomIntegrations.chatroom_uuid==chatroom_uuid).all()
    return {'integrations': integrations, 'messages': chatroom_messages, 'embedding_model': chatroom.embedding_model, 'embedding_provider': chatroom.embedding_provider, 'chat_model': chatroom.chat_model, 'chat_provider': chatroom.chat_provider}

"""Update chatroom name or roles."""
@router.put('/room')
def put_room(request: Request, chatroom_uuid, fields, cookie):
    raise HTTPException(status_code=501, detail='function not implemented')

"""Updates the name for a chatroom"""
@router.put('/roomname')
def put_chatroom_name(request: Request, chatroom_uuid, new_name, cookie, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    chatroom = db.query(Chatrooms).where(Chatrooms.id==chatroom_uuid).one()
    chatroom.name = new_name
    db.commit()

# Only chat provider and model can be updated
@router.put('/roommodel')
def change_chatroom_llm(request: Request, chatroom_uuid, chat_provider, chat_model, cookie, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    chatroom = db.query(Chatrooms).where(Chatrooms.id==chatroom_uuid).one()
    chatroom.chat_model = chat_model
    chatroom.chat_provider = chat_provider
    db.commit()

"""Gets all the chatrooms a user is in"""
@router.get('/rooms')
def get_rooms(request: Request, cookie, db: Session = Depends(get_db)):
    user_uuid = authentication_sdk.User(cookie, request.headers).profile()["user_uuid"]
    chatrooms = db.query(ChatroomRoles).where(ChatroomRoles.user_uuid==user_uuid).all()
    return db.query(Chatrooms).where(Chatrooms.id.in_([chatroom.chatroom_uuid for chatroom in chatrooms])).all()

"""Enables the user to send a message in a chatroom"""
@router.post('/message')
def post_message(request: Request, chatroom_uuid, cookie, message, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    user_uuid = authentication_sdk.User(cookie, headers=request.headers).profile()["user_uuid"]
    message_obj = ChatroomMessages(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid, message=message)
    db.add(message_obj)
    db.commit()

    # notify webhook
    webhooks = db.query(ChatroomWebhooks).where(ChatroomWebhooks.type==ChatroomWebhookType.UserSendMessage).all()
    for webhook in webhooks:
        try:
            requests.post(webhook.url, json={"message": message, "user": user_uuid, 'chatroom_uuid': chatroom_uuid, 'timestamp': str(message_obj.timestamp)})
        except Exception as e:
            print(e)
    
    # Fetch chatroom settings
    c = db.query(Chatrooms).where(Chatrooms.id==chatroom_uuid).one()
    messages = db.query(ChatroomMessages).where(ChatroomMessages.chatroom_uuid==chatroom_uuid).all()

    # Get a response from AI service and store
    history = [{'is_user': m.user_uuid != CHATBOT_UUID, 'message': m.message} for m in messages]
    response = ai_sdk.get_Response(history=history,
                                   chatroom_uuid=chatroom_uuid,
                                   sessionToken=cookie,
                                   headers=request.headers,
                                   embedding_model=c.embedding_model,
                                   chat_model=c.chat_model,
                                   chat_provider=c.chat_provider,
                                   embedding_provider=c.embedding_provider)
    db.add(ChatroomMessages(chatroom_uuid=chatroom_uuid, user_uuid=CHATBOT_UUID, message=response['data']['response'], references=response['data']['citations']))
    db.commit()

"""Deletes a message in a chatroom"""
@router.delete('/message')
def delete_message(request: Request, chatroom_uuid, message_uuid, cookie, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    db.query(ChatroomMessages).where(ChatroomMessages.message_uuid==message_uuid)

"""Deletes all messages in a chatroom"""
@router.delete('/messages')
def delete_messages(request: Request, chatroom_uuid, cookie, db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, chatroom_uuid, cookie, db)
    db.query(ChatroomMessages).where(ChatroomMessages.chatroom_uuid==chatroom_uuid).delete()

class AddIntegrationParams(BaseModel):
    chatroom_uuid: str
    integration: str
    config: dict
    cookie: str

@router.post('/integration')
def add_integration(request: Request, p: AddIntegrationParams = Body(), db: Session = Depends(get_db)):
    ensure_user_in_chatroom(request, p.chatroom_uuid, p.cookie, db)
    integration = ChatroomIntegrations(integration=p.integration, chatroom_uuid=p.chatroom_uuid, config=p.config)
    db.add(integration)
    db.commit()

class DeleteIntegrationParams(BaseModel):
    integration_uuid: str
    cookie: str

@router.delete('/integration')
def add_integration(request: Request, p: DeleteIntegrationParams = Body(), db: Session = Depends(get_db)):
    integration = db.query(ChatroomIntegrations).where(ChatroomIntegrations.id==p.integration_uuid).one()
    ensure_user_in_chatroom(request, integration.chatroom_uuid, p.cookie, db)
    db.query(ChatroomIntegrations).where(ChatroomIntegrations.id==p.integration_uuid).delete()
    db.commit()

class AddWebhookParams(BaseModel):
    url: str
    type: str

@router.post('/webhook')
def add_webhook(request: Request, cookie: str, p: AddWebhookParams = Body(), db: Session = Depends(get_db)):
    is_admin = authentication_sdk.User(cookie, headers=request.headers).profile()["is_admin"]
    if not is_admin: raise HTTPException(status_code=400, detail='admin only')
    webhook = ChatroomWebhooks(url=p.url, type=p.type)
    db.add(webhook)
    db.commit()

class DeleteWebhookParams(BaseModel):
    id: str

@router.delete('/webhook')
def delete_webhook(request: Request, cookie: str, p: DeleteWebhookParams = Body(), db: Session = Depends(get_db)):
    is_admin = authentication_sdk.User(cookie, headers=request.headers).profile()["is_admin"]
    if not is_admin: raise HTTPException(status_code=400, detail='admin only')
    db.query(ChatroomWebhooks).where(ChatroomWebhooks.id==p.id).delete()
    db.commit()

@router.get('/webhooks')
def add_webhook(request: Request, cookie: str, db: Session = Depends(get_db)):
    is_admin = authentication_sdk.User(cookie, headers=request.headers).profile()["is_admin"]
    if not is_admin: raise HTTPException(status_code=400, detail='admin only')
    return db.query(ChatroomWebhooks).all()

@router.get("/docs")
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/chatroom/openapi.json",
        title="Chatroom API Doc"
    )
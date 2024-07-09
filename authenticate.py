from fastapi import HTTPException
from InfoGrep_BackendSDK import authentication_sdk

#apis used to authenticate if a user should be allowed to do some action

def auth_user(user_uuid, cookie):
    #check to see if the user and their session cookie are valid
    try:
        auth = authentication_sdk.User(cookie);
        assert(user_uuid == auth.profile()['username'])
    except:
        raise HTTPException(status_code=401, detail="User or session cookie invalid")
    return;

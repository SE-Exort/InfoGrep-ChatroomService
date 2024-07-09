from fastapi import FastAPI;
import uvicorn
from Endpoints.Endpoints import router
InfoGrepChatroomService = FastAPI();

InfoGrepChatroomService.include_router(router)
if __name__ == "__main__":
    uvicorn.run(InfoGrepChatroomService, host="0.0.0.0", port=8003)
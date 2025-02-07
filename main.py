from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import os

from Endpoints.Endpoints import router
from InfoGrep_BackendSDK.middleware import TracingMiddleware, LoggingMiddleware
from InfoGrep_BackendSDK.infogrep_logger.logger import Logger

InfoGrepChatroomService = FastAPI();

os.environ["no_proxy"]="*"
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
origins = [
    "*",
]

InfoGrepChatroomService.add_middleware(LoggingMiddleware, logger=Logger("ChatroomServiceLogger"))
InfoGrepChatroomService.add_middleware(TracingMiddleware)
InfoGrepChatroomService.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
InfoGrepChatroomService.include_router(router)

if __name__ == "__main__":
    uvicorn.run(InfoGrepChatroomService, host="0.0.0.0", port=8003)
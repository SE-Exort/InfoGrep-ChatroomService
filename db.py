import uuid
from sqlalchemy import JSON, UUID, DateTime, create_engine, func
import os
from sqlalchemy.orm import Session
from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base
import enum
from sqlalchemy import Enum


class ChatroomRole(enum.Enum):
    Owner = 1
    Editor = 2
    Viewer = 3

from InfoGrep_BackendSDK.infogrep_logger.logger import Logger
# DB config
db_port = "5432"
db_host = os.environ.get("PGHOST", f"localhost:{db_port}")
db_user = os.environ.get("POSTGRES_USERNAME", "postgres")
db_password = os.environ.get("POSTGRES_PASSWORD", "example")
db_name = os.environ.get("PG_DATABASE_NAME", "postgres")
logger = Logger("AIServiceLogger")

DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}/{db_name}"

engine = None

# Create SQLAlchemy engine
if os.environ.get("PG_VERIFY_CERT") == "true":
    ca_cert_path = os.environ["PG_CA_CERT_PATH"]
    client_cert_path = os.environ["PG_TLS_CERT_PATH"]
    client_key_path = os.environ["PG_TLS_KEY_PATH"]
    ssl_args = {
        'sslrootcert':ca_cert_path,
        'sslcert':client_cert_path,
        'sslkey':client_key_path
    }
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=ssl_args)
    logger.info("SSL DB engine created")

else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    logger.info("DB engine created")

def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

Base = declarative_base()

class Chatrooms(Base):
    __tablename__ = 'chatrooms'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    embedding_model = Column(String, nullable=False)
    chat_model = Column(String, nullable=False)
    embedding_provider = Column(String, nullable=False)
    chat_provider = Column(String, nullable=False)

class ChatroomRoles(Base):
    __tablename__ = 'chatroom_roles'

    user_uuid = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    chatroom_uuid = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    role = Column(Enum(ChatroomRole), nullable=False)

class ChatroomMessages(Base):
    __tablename__ = 'chatroom_messages'

    message_uuid = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    chatroom_uuid = Column(UUID(as_uuid=True), nullable=False)
    user_uuid = Column(UUID(as_uuid=True), nullable=False)
    message = Column(String, nullable=False)
    references = Column(JSON)

class ChatroomIntegration(str, enum.Enum):
    Confluence = 'confluence'

class ChatroomIntegrations(Base):
    __tablename__ = 'chatroom_integrations'

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid.uuid4)
    integration = Column(Enum(ChatroomIntegration), nullable=False)
    chatroom_uuid = Column(UUID(as_uuid=True), nullable=False)
    config = Column(JSON, nullable=False)

# Create all tables in db
Base.metadata.create_all(engine)

from datetime import datetime;
import psycopg2
import os

from InfoGrep_BackendSDK.infogrep_logger.logger import Logger

class ChatroomDB:
    def __init__(self):
        # init logger
        self.logger = Logger("ChatroomServiceLogger")

        # DB config
        db_port = "5432"
        db_host = os.environ.get("PGHOST", "localhost")
        db_user = os.environ.get("POSTGRES_USERNAME", "postgres")
        db_password = os.environ.get("POSTGRES_PASSWORD", "example")
        db_name = os.environ.get("PG_DATABASE_NAME", "postgres")

        keepalive_kwargs = {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 5,
            "keepalives_count": 5,
        }

        if os.environ.get("PG_VERIFY_CERT") == "true":
            ca_cert_path = os.environ["PG_CA_CERT_PATH"]
            client_cert_path = os.environ["PG_TLS_CERT_PATH"]
            client_key_path = os.environ["PG_TLS_KEY_PATH"]
            self.con = psycopg2.connect(
                database=db_name, user=db_user, password=db_password,
                host=db_host, port=db_port,
                sslmode='verify-full',
                sslrootcert=ca_cert_path, 
                sslcert=client_cert_path, 
                sslkey=client_key_path, 
                **keepalive_kwargs
            )
            self.logger.info("SSL DB connection established")
        else:
            self.con = psycopg2.connect(database=db_name, user=db_user, password=db_password, host=db_host, port=db_port, **keepalive_kwargs);
            self.logger.info("DB connection established")
        
        self.cursor = self.con.cursor();
        self.cursor.execute("CREATE TABLE IF NOT EXISTS chatroomlist (\
                                CHATROOM CHAR(36) NOT NULL,\
                                NAME VARCHAR,\
                                EMBEDDING_MODEL VARCHAR,\
                                CHAT_MODEL VARCHAR,\
                                MODEL_PROVIDER VARCHAR,\
                                PRIMARY KEY(CHATROOM))")
        
        #table to define what users are in a chatroom and their permissions
        self.cursor.execute("CREATE TABLE IF NOT EXISTS chatroomroles (\
                                CHATROOM CHAR(36) NOT NULL,\
                                USERUUID CHAR(36) NOT NULL,\
                                USERROLE VARCHAR NOT NULL,\
                                PERM1 INTEGER NOT NULL,\
                                FOREIGN KEY(CHATROOM) REFERENCES chatroomlist(CHATROOM) ON DELETE CASCADE,\
                                PRIMARY KEY(CHATROOM, USERUUID))")
        
        self.cursor.execute("CREATE TABLE IF NOT EXISTS chatroommessages (\
                                MSGUUID CHAR(36) NOT NULL,\
                                TIME timestamp NOT NULL,\
                                CHATROOM CHAR(36) NOT NULL,\
                                USERUUID CHAR(36) NOT NULL,\
                                MESSAGE VARCHAR NOT NULL,\
                                FOREIGN KEY(CHATROOM) REFERENCES chatroomlist(CHATROOM) ON DELETE CASCADE,\
                                PRIMARY KEY(MSGUUID))")
        
    def createChatroom(self, chatroom_uuid, chatroom_name, embedding_model, chat_model, provider, user_uuid):
        self.cursor.execute("INSERT INTO chatroomlist (CHATROOM, NAME, EMBEDDING_MODEL, CHAT_MODEL, MODEL_PROVIDER) VALUES(%s, %s, %s, %s, %s);", (str(chatroom_uuid),str(chatroom_name), str(embedding_model), str(chat_model), str(provider)))
        self.joinRoom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)
        self.con.commit()
        return
    
    def getChatroomEmbeddingModel(self, chatroom_uuid):
        self.cursor.execute("SELECT EMBEDDING_MODEL FROM chatroomlist WHERE CHATROOM = %s", (str(chatroom_uuid),))
        return self.cursor.fetchone()[0]
    
    def getChatroomChatModel(self, chatroom_uuid):
        self.cursor.execute("SELECT CHAT_MODEL FROM chatroomlist WHERE CHATROOM = %s", (str(chatroom_uuid),))
        return self.cursor.fetchone()[0]
    
    def getChatroomModelProvider(self, chatroom_uuid):
        self.cursor.execute("SELECT MODEL_PROVIDER FROM chatroomlist WHERE CHATROOM = %s", (str(chatroom_uuid),))
        return self.cursor.fetchone()[0]

    def deleteChatroom(self, chatroom_uuid):
        self.cursor.execute("DELETE FROM chatroomlist WHERE CHATROOM = %s;", (str(chatroom_uuid),));
        self.con.commit();
        return;

    def getChatrooms(self, user_uuid):
        self.cursor.execute("SELECT list.CHATROOM, list.NAME, list.CHAT_MODEL, list.EMBEDDING_MODEL, list.MODEL_PROVIDER FROM chatroomlist list INNER JOIN chatroomroles roles ON list.CHATROOM = roles.CHATROOM WHERE USERUUID = %s", (str(user_uuid),))
        userroomslist = self.cursor.fetchall();
        return userroomslist
    
    def getMessages(self, chatroom_uuid):
        self.cursor.execute("SELECT USERUUID, TIME, MSGUUID, MESSAGE FROM chatroommessages WHERE CHATROOM = %s", (str(chatroom_uuid),))
        message = self.cursor.fetchall();
        return message

    def getMessage(self, chatroom_uuid, message_uuid):
        self.cursor.execute("SELECT MESSAGE FROM chatroommessages WHERE CHATROOM = %s AND MSGUUID = %s", (str(chatroom_uuid), str(message_uuid)))
        message = self.cursor.fetchall();
        return message
    
    def createMessage(self, chatroom_uuid, user_uuid, message_uuid, message):
        self.cursor.execute("INSERT INTO chatroommessages (MSGUUID,TIME,CHATROOM,USERUUID,MESSAGE) VALUES(%s,%s,%s,%s,%s)", (str(message_uuid), str(datetime.now()) ,str(chatroom_uuid), str(user_uuid), str(message)))
        self.con.commit();
        return;

    def deleteMessage(self, chatroom_uuid, message_uuid):
        self.cursor.execute("DELETE FROM chatroommessages WHERE CHATROOM = %s AND MSGUUID = %s;", (str(chatroom_uuid),str(message_uuid)));
        self.con.commit();
        return;

    def deleteMessages(self, chatroom_uuid):
        self.cursor.execute("DELETE FROM chatroommessages WHERE CHATROOM = %s;", (str(chatroom_uuid),));
        self.con.commit();
        return;

    def userInRoom(self, chatroom_uuid, user_uuid):
        self.cursor.execute("SELECT CHATROOM FROM chatroomroles WHERE CHATROOM = %s AND USERUUID = %s", (str(chatroom_uuid), str(user_uuid)))
        userroom = self.cursor.fetchall();
        if not userroom:
            return False;
        return True;

    def joinRoom(self, chatroom_uuid, user_uuid):
        self.cursor.execute("INSERT INTO chatroomroles (CHATROOM,USERUUID,USERROLE,PERM1) VALUES(%s,%s,'OWNER',1)", (str(chatroom_uuid), str(user_uuid)))
        self.con.commit();
        return;

    def updateRoomName(self, chatroom_uuid, chatroom_name):
        self.cursor.execute("UPDATE chatroomlist SET NAME = %s WHERE CHATROOM = %s", (str(chatroom_name), str(chatroom_uuid)));
        self.con.commit();
        return;
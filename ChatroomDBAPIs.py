import sqlite3
import time

class ChatroomDB:
    def __init__(self):
        self.con = sqlite3.connect("chatroomdb.db", check_same_thread=False);
        self.con.execute('PRAGMA foreign_keys = ON;')
        self.cursor = self.con.cursor();
        self.cursor.execute("CREATE TABLE IF NOT EXISTS chatroomlist (\
                                CHATROOM CHAR(37) NOT NULL,\
                                NAME VARCHAR,\
                                PRIMARY KEY(CHATROOM))")
        
        #table to define what users are in a chatroom and their permissions
        self.cursor.execute("CREATE TABLE IF NOT EXISTS chatroomroles (\
                                CHATROOM CHAR(37) NOT NULL,\
                                USERUUID CHAR(37) NOT NULL,\
                                USERROLE VARCHAR NOT NULL,\
                                PERM1 INTEGER NOT NULL,\
                                FOREIGN KEY(CHATROOM) REFERENCES chatroomlist(CHATROOM) ON DELETE CASCADE,\
                                PRIMARY KEY(CHATROOM, USERUUID))")
        
        self.cursor.execute("CREATE TABLE IF NOT EXISTS chatroommessages (\
                                MSGUUID CHAR(37) NOT NULL,\
                                TIMESTAMP INT NOT NULL,\
                                CHATROOM CHAR(37) NOT NULL,\
                                USERUUID CHAR(37) NOT NULL,\
                                MESSAGE VARCHAR NOT NULL,\
                                FOREIGN KEY(CHATROOM) REFERENCES chatroomlist(CHATROOM) ON DELETE CASCADE,\
                                PRIMARY KEY(MSGUUID))")
        
    def createChatroom(self, chatroom_uuid, chatroom_name, user_uuid):
        self.cursor.execute("INSERT INTO chatroomlist (CHATROOM, NAME) VALUES(?, ?);", (str(chatroom_uuid),str(chatroom_name)));
        self.joinRoom(chatroom_uuid=chatroom_uuid, user_uuid=user_uuid)
        self.con.commit();
        return;

    def deleteChatroom(self, chatroom_uuid):
        self.cursor.execute("DELETE FROM chatroomlist WHERE CHATROOM = ?;", (str(chatroom_uuid),));
        self.con.commit();
        return;

    def getChatrooms(self, user_uuid):
        self.cursor.execute("SELECT list.CHATROOM, list.NAME FROM chatroomlist list INNER JOIN chatroomroles roles ON list.CHATROOM = roles.CHATROOM WHERE USERUUID = ?", (str(user_uuid),))
        userroomslist = self.cursor.fetchall();
        return userroomslist
    
    def getMessages(self, chatroom_uuid):
        self.cursor.execute("SELECT USERUUID, TIMESTAMP, MSGUUID, MESSAGE FROM chatroommessages WHERE CHATROOM = ?", (str(chatroom_uuid),))
        message = self.cursor.fetchall();
        return message

    def getMessage(self, chatroom_uuid, message_uuid):
        self.cursor.execute("SELECT MESSAGE FROM chatroommessages WHERE CHATROOM = ? AND MSGUUID = ?", (str(chatroom_uuid), str(message_uuid)))
        message = self.cursor.fetchall();
        return message
    
    def createMessage(self, chatroom_uuid, user_uuid, message_uuid, message):
        timestamp = time.time_ns()
        self.cursor.execute("INSERT INTO chatroommessages (MSGUUID,TIMESTAMP,CHATROOM,USERUUID,MESSAGE) VALUES(?,?,?,?,?)", (str(message_uuid), timestamp, str(chatroom_uuid), str(user_uuid), str(message)))
        self.con.commit();
        return;

    def deleteMessage(self, chatroom_uuid, message_uuid):
        self.cursor.execute("DELETE FROM chatroommessages WHERE CHATROOM = ? AND MSGUUID = ?;", (str(chatroom_uuid),str(message_uuid)));
        self.con.commit();
        return;

    def deleteMessages(self, chatroom_uuid):
        self.cursor.execute("DELETE FROM chatroommessages WHERE CHATROOM = ?;", (str(chatroom_uuid)));
        self.con.commit();
        return;

    def userInRoom(self, chatroom_uuid, user_uuid):
        self.cursor.execute("SELECT CHATROOM FROM chatroomroles WHERE CHATROOM = ? AND USERUUID = ?", (str(chatroom_uuid), str(user_uuid)))
        userroom = self.cursor.fetchall();
        if not userroom:
            return False;
        return True;

    def joinRoom(self, chatroom_uuid, user_uuid):
        self.cursor.execute("INSERT INTO chatroomroles (CHATROOM,USERUUID,USERROLE,PERM1) VALUES(?,?,'OWNER',1)", (str(chatroom_uuid), str(user_uuid)))
        self.con.commit();
        return;

    def updateRoomName(self, chatroom_uuid, chatroom_name):
        self.cursor.execute("UPDATE chatroomlist SET NAME = ? WHERE CHATROOM = ?", (str(chatroom_name), str(chatroom_uuid)));
        self.con.commit();
        return;
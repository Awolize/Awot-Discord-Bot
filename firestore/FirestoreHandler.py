import firebase_admin
import google.cloud
from firebase_admin import credentials, firestore

cred = credentials.Certificate("./firestore/serviceAccountKey.json")
app = firebase_admin.initialize_app(cred)

class FirestoreHandler():
    def __init__(self):
        self.db = firestore.client()
        self.batch = self.db.batch()
        self.userServerDict = dict()
        self.serverDict = dict()

    def main(self, user_id: int, names: list, statusList: list, gamesList: list, current_name: str, avatarUrl: str):

        # Set Current name in the firestore database
        try:
            # Add user to users table
            data = {
                u'Id': user_id,
                u'Name': current_name,
                u'Names': names,
                u'Status': {
                    u'Online': statusList[0],
                    u'Idle': statusList[1],
                    u'Busy': statusList[2],
                    u'Offline': statusList[3]
                },
                u'Games': gamesList,
                u'IconUrl': avatarUrl,
            }
            db_ref = self.db.collection('users').document(str(user_id))
            self.batch.set(db_ref, data) 

        except Exception as e:
            print("[Error] FirestoreHandler.py -> add_user() -> Exception: {}".format(e))

    def addServersToUsers(self, userID: str, serverId: int, serverName: str, serverIconUrl: str):
        if str(userID) not in self.userServerDict:
            self.userServerDict[str(userID)] = list()

        serverData = {
            "id": str(serverId),
            "name": serverName,
            "iconUrl": serverIconUrl
        }
        self.userServerDict[str(userID)].append(serverData)

    def addServers(self, serverId: str, serverName: str, serverIconUrl: str, userList: list):
        serverData = {
            "Id": serverId,
            "Name": serverName,
            "IconUrl": serverIconUrl,
            'Users': userList
        }
        pass

        if serverId not in self.serverDict:
            self.serverDict[serverId] = dict()
        self.serverDict[serverId] = serverData

    def addServersToUsers_done(self):
        # Skriv om för mindre firebase usage
        for user_id, serverList in self.userServerDict.items():
            try:
                data = {
                    u'Servers': serverList
                }
                db_ref = self.db.collection('users').document(str(user_id))
                self.batch.update(db_ref, data) # 

            except Exception as e:
                print("[Error] FirestoreHandler.py -> addServersToUsers_done() -> Exception: {}".format(e))

        print
        for serverId in self.serverDict:
            try:
                db_ref = self.db.collection('servers').document(serverId)
                self.batch.set(db_ref, self.serverDict[serverId])

            except Exception as e:
                print("[Error] FirestoreHandler.py -> addServersToUsers_done()_p2 -> Exception: {}".format(e))

    def commit(self):
        print("firestore batch commit...")
        self.batch.commit()
        print("firestore batch commit, done.")


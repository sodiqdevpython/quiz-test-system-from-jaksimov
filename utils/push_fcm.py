import firebase_admin
from firebase_admin import credentials, messaging
from pathlib import Path

cred_path = Path(__file__).resolve().parent.parent / "serviceAccount.json"
cred = credentials.Certificate(str(cred_path))

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

def send_push_fcm(token: str, title: str, body: str):
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token
    )
    return messaging.send(message)

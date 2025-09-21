# utils/push.py
import json
from pathlib import Path
from pywebpush import webpush, WebPushException
from cryptography.hazmat.primitives import serialization

# BASE_DIR = project root (manage.py turgan joy)
BASE_DIR = Path(__file__).resolve().parents[1]

# 1) private.pem ni BEVOSITA fayldan o‘qiymiz (settings’dan OLMAYMIZ!)
_RAW_PEM = (BASE_DIR / "private.pem").read_text(encoding="utf-8").strip()

# 2) PEM ni load qilib, kanonik PKCS8 PEM sifatida qayta eksport qilamiz
_priv_obj = serialization.load_pem_private_key(_RAW_PEM.encode("utf-8"), password=None)
_VAPID_PRIVATE_PEM = _priv_obj.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")

def send_push(user, title, body):
    payload = {"title": title, "body": body}

    for sub in user.pushsubscription_set.all():
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps(payload),
                vapid_private_key=_VAPID_PRIVATE_PEM,   # ← faqat shu PEM ketadi
                vapid_claims={"sub": "mailto:admin@example.com"},
            )
        except WebPushException as ex:
            status = getattr(getattr(ex, "response", None), "status_code", None)
            if status in (404, 410):
                sub.delete()
            else:
                print("Push error:", repr(ex))

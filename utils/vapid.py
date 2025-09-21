from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

def load_vapid_public_key_base64url(pem_path: str) -> str:
    with open(pem_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())

    der = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    return base64.urlsafe_b64encode(der).decode("utf-8").rstrip("=")

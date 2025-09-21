# generate_keys.py
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Private key yaratamiz
private_key = ec.generate_private_key(ec.SECP256R1())

# Public key (Uncompressed Point, X9.62 formatida)
public_key = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint,
)

# base64url funksiyasi
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

# 32-byte integer sifatida private key
private_bytes = private_key.private_numbers().private_value.to_bytes(32, "big")

print("VAPID_PRIVATE_KEY=", b64url(private_bytes))
print("VAPID_PUBLIC_KEY=", b64url(public_key))

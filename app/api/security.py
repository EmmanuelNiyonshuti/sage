import hashlib
import uuid


def generate_api_key():
    return str(uuid.uuid4())


def hash_api_key(api_key: str) -> str:
    api_key_hash = hashlib.sha256(api_key.encode())
    return api_key_hash.hexdigest()

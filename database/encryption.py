from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

# Генерация ключа шифрования при первом запуске
def get_encryption_key():
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        key = Fernet.generate_key()
        with open(".env", "a") as f:
            f.write(f"\nENCRYPTION_KEY={key.decode()}")
    return key.encode() if isinstance(key, str) else key

fernet = Fernet(get_encryption_key())

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode() 
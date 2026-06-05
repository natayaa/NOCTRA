from argon2 import PasswordHasher, exceptions

hasher = PasswordHasher()

def create_hash_password(plain_password: str) -> str:
    if not plain_password: return False
    
    return hasher.hash(plain_password)

def verify_hashed_password(plain_password: str, hashed_password: str) -> bool:
    try:
        hasher.verify(hash=hashed_password, password=plain_password)
        return True
    except exceptions.VerifyMismatchError as mismatch:
        return False
    except exceptions.InvalidHashError:
        return False
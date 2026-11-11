import hashlib
import hmac
import secrets


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 240_000).hex()
    return f"pbkdf2_sha256$240000${salt}${digest}"


def check_password(stored, password):
    try:
        algorithm, rounds, salt, digest = stored.split("$")
        hash_name = algorithm[len("pbkdf2_"):] if algorithm.startswith("pbkdf2_") else algorithm
        candidate = hashlib.pbkdf2_hmac(
            hash_name, password.encode(), salt.encode(), int(rounds)
        ).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False

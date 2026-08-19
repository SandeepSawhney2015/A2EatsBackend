import jwt
from jwt import PyJWKClient

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

jwt_client = PyJWKClient(APPLE_KEYS_URL)

def verify_apple_token(token: str) -> dict:
    signing_key = jwt_client.get_signing_key_from_jwt(token)
    decode = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=APPLE_ISSUER,
    )
    return decode
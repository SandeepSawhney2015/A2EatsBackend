import jwt
from jwt import PyJWKClient
from app.core.config import get_settings

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

jwt_client = PyJWKClient(APPLE_KEYS_URL)

def verify_apple_token(token: str) -> dict:
    signing_key = jwt_client.get_signing_key_from_jwt(token)
    decode = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=get_settings().apple_bundle_id,
        issuer=APPLE_ISSUER,
    )
    return decode
import jwt
import json

from datetime import datetime, timedelta

payload = {
    "sub": "user123",
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(days=7)
}

token = jwt.encode(payload, "super-secure-key", algorithm="HS256")

user_token = json.dumps({"token": token})

print(user_token)

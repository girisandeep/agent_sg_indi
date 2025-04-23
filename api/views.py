import json
import jwt
import sqlalchemy
import pandas as pd
from sqlglot import parse_one, exp
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from config import JWT_SECRET, JWT_ALGORITHM, MAX_ROWS, QUERY_LOG_PATH

with open("user_db.json") as f:
    USER_MAP = json.load(f)

def decode_jwt(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise ValueError("Missing or malformed token")
    token = auth.replace("Bearer ", "")
    decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    user_id = decoded.get("sub")
    if user_id not in USER_MAP:
        raise ValueError("Unauthorized user")
    return user_id, USER_MAP[user_id]["databases"]

@api_view(["POST"])
def list_databases(request):
    try:
        user_id, dbs = decode_jwt(request)
        return Response({db:'' for db in dbs.keys()})
    except Exception as e:
        return Response({"error": str(e)}, status=403)

@api_view(["POST"])
def list_tables(request):
    try:
        user_id, dbs = decode_jwt(request)
        db = request.data.get("database")
        if db not in dbs:
            return Response({"error": "Invalid database"}, status=400)
        engine = sqlalchemy.create_engine(dbs[db])
        inspector = sqlalchemy.inspect(engine)

        return Response({tn:tn for tn in inspector.get_table_names()})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(["POST"])
def execute_sql(request):
    try:
        user_id, dbs = decode_jwt(request)
        db = request.data.get("database")
        query = request.data.get("query")

        if db not in dbs:
            return Response({"error": "Invalid database"}, status=400)

        parsed = parse_one(query)
        if not isinstance(parsed, exp.Select):
            return Response({"error": "Only SELECT queries allowed"}, status=403)

        final_query = parsed.sql()
        engine = sqlalchemy.create_engine(dbs[db])
        df = pd.read_sql_query(final_query, engine)

        with open(QUERY_LOG_PATH, "a") as f:
            f.write(f"User: {user_id}\nOriginal: {query}\nFinal:    {final_query}\n{'='*40}\n")

        return Response(df.to_dict(orient="records"))
    except jwt.ExpiredSignatureError:
        return Response({"error": "Token expired"}, status=401)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

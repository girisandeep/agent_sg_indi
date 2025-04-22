# sqlshield.py
import requests, json

class SQLShield:
    def __init__(self, api_url: str, token_file="/workspace/config/user_token.json"):
        with open(token_file) as f:
            self.token = json.load(f)["token"]
        self.api_url = api_url.rstrip("/")

    def _request(self, endpoint, payload=None):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.post(f"{self.api_url}/{endpoint}", json=payload or {}, headers=headers)
        response.raise_for_status()
        return response.json()

    def list_databases(self):
        return self._request("list_databases")

    def list_tables(self, db):
        return self._request("list_tables", {"database": db})

    def run_sql(self, db, query):
        return self._request("run_sql", {"database": db, "query": query})

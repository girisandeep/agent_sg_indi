# terno.py
import requests, json
import pandas as pd

class TernoClient:
    def __init__(self, api_url='http://host.docker.internal:8000/api', token_file="/workspace/config/user_token.json"):
        with open(token_file) as f:
            self.token = json.load(f)["token"]
        self.api_url = api_url.rstrip("/")
    def _request(self, endpoint, payload=None):
        headers = {'Authorization': f'Bearer {self.token}'}
        response = requests.post(f"{self.api_url}/{endpoint}", json=payload or {}, headers=headers)
        response.raise_for_status()
        return response.json()
    
ternoclient = TernoClient()

def list_databases():
    return ternoclient._request("list_databases")

def list_tables(db):
    return ternoclient._request("list_tables", {"database": db})

def run_sql(db, query):
    df_dict = ternoclient._request("run_sql", {"database": db, "query": query})
    return pd.DataFrame(df_dict)

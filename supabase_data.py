"""
Datová vrstva pro Supabase — náhrada za file-based user_data.py.
Používá se automaticky když jsou dostupné Supabase credentials v st.secrets.
"""
import json
import copy
import streamlit as st
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client | None:
    global _client
    if _client is not None:
        return _client
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        if url and key:
            _client = create_client(url, key)
            return _client
    except Exception:
        pass
    return None


def is_available() -> bool:
    return get_client() is not None


# ---------- USERS ----------

def user_exists(username: str) -> bool:
    c = get_client()
    if not c:
        return False
    res = c.table("users").select("username").eq("username", username).execute()
    return len(res.data) > 0


def get_all_credentials() -> dict:
    """Vrátí credentials ve formátu pro streamlit-authenticator."""
    c = get_client()
    if not c:
        return {"usernames": {}}
    res = c.table("users").select("*").execute()
    usernames = {}
    for row in res.data:
        usernames[row["username"]] = {
            "email": "",
            "name": row["name"],
            "password": row["password_hash"],
        }
    return {"usernames": usernames}


def create_user(username: str, name: str, password_hash: str) -> bool:
    c = get_client()
    if not c:
        return False
    try:
        c.table("users").insert({
            "username": username,
            "name": name,
            "password_hash": password_hash,
        }).execute()
        return True
    except Exception as e:
        st.error(f"Chyba při vytváření účtu: {e}")
        return False


# ---------- PROJECTS ----------

def load_user_projects(username: str) -> dict:
    c = get_client()
    if not c:
        return {}
    res = c.table("projects").select("project_name, project_data, is_public").eq("username", username).execute()
    result = {}
    for row in res.data:
        data = row["project_data"]
        if isinstance(data, str):
            data = json.loads(data)
        data["is_public"] = row["is_public"]
        result[row["project_name"]] = data
    return result


def save_user_projects(username: str, projects: dict) -> bool:
    c = get_client()
    if not c:
        return False
    try:
        # Upsert každý projekt zvlášť
        for project_name, project_data in projects.items():
            data = copy.deepcopy(project_data)
            is_public = data.pop("is_public", False)
            c.table("projects").upsert({
                "username": username,
                "project_name": project_name,
                "project_data": data,
                "is_public": is_public,
                "updated_at": "now()",
            }, on_conflict="username,project_name").execute()

        # Smazat projekty které již v dict nejsou
        res = c.table("projects").select("project_name").eq("username", username).execute()
        existing_names = {row["project_name"] for row in res.data}
        to_delete = existing_names - set(projects.keys())
        for name in to_delete:
            c.table("projects").delete().eq("username", username).eq("project_name", name).execute()

        return True
    except Exception as e:
        st.error(f"Chyba při ukládání projektů: {e}")
        return False


def load_shared_projects() -> dict:
    c = get_client()
    if not c:
        return {}
    res = c.table("projects").select("project_name, project_data, username").eq("is_public", True).execute()
    shared = {}
    for row in res.data:
        data = row["project_data"]
        if isinstance(data, str):
            data = json.loads(data)
        key = f"{row['project_name']} [{row['username']}]"
        shared[key] = copy.deepcopy(data)
        shared[key]["_owner"] = row["username"]
        shared[key]["_readonly"] = True
    return shared


def set_project_visibility(username: str, project_name: str, is_public: bool) -> bool:
    c = get_client()
    if not c:
        return False
    try:
        c.table("projects").update({"is_public": is_public}).eq("username", username).eq("project_name", project_name).execute()
        return True
    except Exception:
        return False

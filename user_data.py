import json
import copy
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
SHARED_DIR = DATA_DIR / "shared"
KROKY_PATH = DATA_DIR / "kroky.json"
KROKY_CUSTOM_PATH = DATA_DIR / "kroky_custom.json"


def _ensure_dirs(username: str):
    user_dir = USERS_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    return user_dir


def _load(path: Path) -> dict:
    try:
        if path.exists() and path.stat().st_size > 2:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[ERROR] load {path}: {e}")
    return {}


def _save(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] save {path}: {e}")
        return False


def get_user_projects_path(username: str) -> Path:
    return USERS_DIR / username / "projects.json"


def load_user_projects(username: str) -> dict:
    """Load private projects for a user."""
    _ensure_dirs(username)
    return _load(get_user_projects_path(username))


def save_user_projects(username: str, data: dict) -> bool:
    """Save private projects for a user."""
    _ensure_dirs(username)
    return _save(get_user_projects_path(username), data)


def load_shared_projects() -> dict:
    """Load all public projects from all users."""
    shared: dict = {}
    if not USERS_DIR.exists():
        return shared
    for user_dir in USERS_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        projects = _load(user_dir / "projects.json")
        for proj_name, proj_data in projects.items():
            if proj_data.get("is_public", False):
                key = f"{proj_name} [{user_dir.name}]"
                shared[key] = copy.deepcopy(proj_data)
                shared[key]["_owner"] = user_dir.name
                shared[key]["_readonly"] = True
    return shared


def set_project_visibility(username: str, project_name: str, is_public: bool) -> bool:
    """Toggle public/private on a project."""
    projects = load_user_projects(username)
    if project_name not in projects:
        return False
    projects[project_name]["is_public"] = is_public
    return save_user_projects(username, projects)


def load_kroky() -> dict:
    """Load shared action templates."""
    data = _load(KROKY_PATH)
    if not data:
        data = _load(KROKY_CUSTOM_PATH)
    custom = _load(KROKY_CUSTOM_PATH)
    data.update(custom)
    return data


def save_kroky(data: dict) -> bool:
    """Save shared action templates."""
    ordered = dict(sorted(data.items(), key=lambda kv: kv[0].lower()))
    ok = _save(KROKY_PATH, ordered)
    _save(KROKY_CUSTOM_PATH, ordered)
    return ok


def list_all_users() -> list[str]:
    """Return list of registered usernames."""
    if not USERS_DIR.exists():
        return []
    return [d.name for d in USERS_DIR.iterdir() if d.is_dir()]

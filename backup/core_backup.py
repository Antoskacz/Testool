import json
import re
import pandas as pd
from pathlib import Path
import copy
from datetime import datetime
import unicodedata

# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"

KROKY_PATH = DATA_DIR / "kroky.json"
PROJECTS_PATH = DATA_DIR / "projects.json"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ---------- CONSTANTS ----------
SYSTEM_APPLICATION = "Siebel_CZ"
TEST_TYPE = "Manual"
TEST_PHASE = "4-User Acceptance"

PRIORITY_MAP = {
    "1": "1-High",
    "2": "2-Medium", 
    "3": "3-Low"
}

COMPLEXITY_MAP = {
    "1": "1-Giant",
    "2": "2-Huge",
    "3": "3-Big",
    "4": "4-Medium",
    "5": "5-Low"
}

# ---------- HELPER FUNCTIONS ----------
def load_json(filepath):
    """Safe JSON loading"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def save_json(filepath, data):
    """Safe JSON saving"""
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

# ---------- TEXT PROCESSING ----------
def extract_channel(text: str) -> str:
    """Extract channel from text"""
    t = text.lower()
    if "shop" in t:
        return "SHOP"
    if "il" in t:
        return "IL"
    return "UNKNOWN"

def extract_segment(text: str) -> str:
    """Extract segment from text"""
    t = text.lower()
    if "b2c" in t:
        return "B2C"
    if "b2b" in t:
        return "B2B"
    return "UNKNOWN"

def extract_technology(text: str) -> str:
    """Extract technology from text"""
    t = text.lower()
    if "hlas" in t or "voice" in t:
        return "HLAS"
    if "fwa" in t and "bisi" in t:
        return "FWA_BISI"
    if "fwa" in t and re.search(r"\bbi\b", t):
        return "FWA_BI"
    for key in ["dsl", "fiber", "cable"]:
        if key in t:
            return key.upper()
    if "fwa" in t:
        return "FWA"
    return "UNKNOWN"

def normalize_text(text):
    """Normalize text for filenames"""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.replace(" ", "_").replace("__", "_")

# ---------- TEST CASE GENERATION ----------
def build_test_name(order: int, sentence: str) -> str:
    """Build test case name from order and sentence"""
    channel = extract_channel(sentence)
    segment = extract_segment(sentence)
    technology = extract_technology(sentence)
    
    prefix = f"{order:03d}_{channel}_{segment}_{technology}"
    return f"{prefix}_{sentence.strip().capitalize()}"

def detect_action(text: str, steps_data: dict) -> str:
    """Detect action from text"""
    t = text.lower()
    for action in steps_data.keys():
        if action.lower() in t:
            return action
    return None

def get_steps_from_action(action: str, steps_data: dict):
    """Get steps for specific action (with deep copy)"""
    if action in steps_data:
        action_data = steps_data[action]
        if isinstance(action_data, dict) and "steps" in action_data:
            return copy.deepcopy(action_data["steps"])
        elif isinstance(action_data, list):
            return copy.deepcopy(action_data)
    return []

def generate_testcase(project: str, sentence: str, action: str, priority: str, 
                     complexity: str, steps_data: dict, projects_data: dict):
    """Generate a new test case"""
    # Get project data
    if project not in projects_data:
        projects_data[project] = {
            "next_id": 1,
            "subject": "UAT2\\Antosova\\",
            "scenarios": []
        }
    
    # Get next ID
    order = projects_data[project]["next_id"]
    projects_data[project]["next_id"] += 1
    
    # Build test case
    test_name = build_test_name(order, sentence)
    segment = extract_segment(sentence)
    channel = extract_channel(sentence)
    
    test_case = {
        "order_no": order,
        "test_name": test_name,
        "akce": action,
        "segment": segment,
        "kanal": channel,
        "priority": priority,
        "complexity": complexity,
        "veta": sentence,
        "kroky": get_steps_from_action(action, steps_data)
    }
    
    # Add to project
    projects_data[project]["scenarios"].append(test_case)
    
    # Save
    save_json(PROJECTS_PATH, projects_data)
    
    return test_case

# ---------- ACTION MANAGEMENT ----------
def add_new_action(action_name: str, description: str, steps: list):
    """Add new action to kroky.json"""
    steps_data = load_json(KROKY_PATH)
    
    steps_data[action_name] = {
        "description": description,
        "steps": steps
    }
    
    return save_json(KROKY_PATH, steps_data)

def update_action(action_name: str, description: str, steps: list):
    """Update existing action in kroky.json"""
    steps_data = load_json(KROKY_PATH)
    
    if action_name in steps_data:
        steps_data[action_name] = {
            "description": description,
            "steps": steps
        }
        return save_json(KROKY_PATH, steps_data)
    
    return False

def delete_action(action_name: str):
    """Delete action from kroky.json"""
    steps_data = load_json(KROKY_PATH)
    
    if action_name in steps_data:
        del steps_data[action_name]
        return save_json(KROKY_PATH, steps_data)
    
    return False

# ---------- EXPORT ----------
def export_to_excel(project_name: str, projects_data: dict):
    """Export project to Excel"""
    if project_name not in projects_data:
        return None
    
    project_data = projects_data[project_name]
    subject = project_data.get("subject", "UAT2\\Antosova\\")
    rows = []
    
    for tc in project_data.get("scenarios", []):
        for i, step in enumerate(tc.get("kroky", []), start=1):
            desc = ""
            exp = ""
            
            if isinstance(step, dict):
                desc = step.get("description", "")
                exp = step.get("expected", "")
            elif isinstance(step, str):
                desc = step
                exp = ""
            
            rows.append({
                "Project": project_name,
                "Subject": subject,
                "System/Application": SYSTEM_APPLICATION,
                "Description": f"Segment: {tc.get('segment', '')}\nChannel: {tc.get('kanal', '')}\nAction: {tc.get('akce', '')}",
                "Type": TEST_TYPE,
                "Test Phase": TEST_PHASE,
                "Test: Test Phase": TEST_PHASE,
                "Test Priority": tc.get("priority", ""),
                "Test Complexity": tc.get("complexity", ""),
                "Test Name": tc.get("test_name", ""),
                "Step Name (Design Steps)": str(i),
                "Description (Design Steps)": desc,
                "Expected (Design Steps)": exp
            })
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    
    # Create output in memory
    import io
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Test Cases')
    
    output.seek(0)
    return output

# ---------- DATA ANALYSIS ----------
def analyze_scenarios(scenarios: list):
    """Analyze scenarios for tree structure display"""
    segment_data = {"B2C": {}, "B2B": {}}
    
    for scenario in scenarios:
        segment = scenario.get("segment", "UNKNOWN")
        channel = scenario.get("kanal", "UNKNOWN")
        test_name = scenario.get("test_name", "")
        action = scenario.get("akce", "UNKNOWN")
        
        # Detect technology
        technology = "DSL"
        tech_keywords = {
            "FIBER": "FIBER",
            "FWA_BISI": "FWA BISI",
            "FWA_BI": "FWA BI",
            "CABLE": "CABLE",
            "HLAS": "HLAS",
            "DSL": "DSL"
        }
        
        for keyword, tech in tech_keywords.items():
            if keyword in test_name.upper():
                technology = tech
                break
        
        # Organize data
        if segment not in segment_data:
            segment_data[segment] = {}
        
        if channel not in segment_data[segment]:
            segment_data[segment][channel] = {}
            
        if technology not in segment_data[segment][channel]:
            segment_data[segment][channel][technology] = []
            
        if action not in segment_data[segment][channel][technology]:
            segment_data[segment][channel][technology].append(action)
    
    return segment_data

def get_automatic_complexity(step_count: int):
    """Get automatic complexity based on step count"""
    if step_count <= 5:
        return "5-Low"
    elif step_count <= 10:
        return "4-Medium"
    elif step_count <= 15:
        return "3-Big"
    elif step_count <= 20:
        return "2-Huge"
    else:
        return "1-Giant"
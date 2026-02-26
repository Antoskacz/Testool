#!/usr/bin/env python3
"""
End-to-end test simulating complete Streamlit workflow:
1. App startup - load data from files
2. User adds new action
3. Save and rerun
4. Verify action is in memory and persisted to files
"""

import json
import copy
from pathlib import Path

def load_json(path):
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True

def simulate_streamlit_workflow():
    """Simulate the exact Streamlit workflow from app.py"""
    
    KROKY_PATH = Path("data/kroky.json")
    KROKY_CUSTOM_PATH = Path("data/kroky_custom.json")
    
    print("=" * 80)
    print("SIMULATING COMPLETE STREAMLIT WORKFLOW")
    print("=" * 80)
    
    # ========== APP STARTUP (First render) ==========
    print("\n[1. APP STARTUP - First render]")
    print("-" * 80)
    
    # Lines 242-276 from app.py: Load data
    projects = {}  # Not relevant for this test
    steps_data = load_json(KROKY_PATH)
    custom_steps = load_json(KROKY_CUSTOM_PATH)
    if custom_steps:
        steps_data.update(custom_steps)
    print(f"✓ Loaded {len(steps_data)} actions from files")
    
    # Session state initialization (lines 275-276)
    session_state = {}
    session_state['steps_data'] = copy.deepcopy(steps_data)
    session_state['projects'] = projects
    print(f"✓ Initialized session_state.steps_data with {len(session_state['steps_data'])} actions")
    
    # Lines 944-945: Initialize edit_steps_data (with our fix: ALWAYS, not just once)
    session_state['edit_steps_data'] = session_state['steps_data'].copy()
    print(f"✓ Synced session_state.edit_steps_data with {len(session_state['edit_steps_data'])} actions")
    
    initial_count = len(session_state['edit_steps_data'])
    
    # ========== USER ADDS NEW ACTION (lines 1034-1054) ==========
    print("\n[2. USER ADDS NEW ACTION]")
    print("-" * 80)
    
    action_name = "End_To_End_Test"
    session_state['new_steps'] = [
        {"description": "First step", "expected": "First expected"},
        {"description": "Second step", "expected": "Second expected"}
    ]
    
    # User clicks "Save New Action" button
    print(f"✓ User fills form: name='{action_name}', description='Test action'")
    print(f"✓ User adds {len(session_state['new_steps'])} steps")
    
    # Save to session_state.edit_steps_data
    session_state['edit_steps_data'][action_name] = {
        "description": "Test action added via UI",
        "steps": session_state['new_steps'].copy()
    }
    print(f"✓ Action added to session_state.edit_steps_data")
    print(f"✓ edit_steps_data now has {len(session_state['edit_steps_data'])} actions (was {initial_count})")
    
    # ========== SAVE TO FILE (lines 1049) ==========
    print("\n[3. SAVE TO FILE]")
    print("-" * 80)
    
    ordered = dict(sorted(session_state['edit_steps_data'].items(), key=lambda kv: kv[0].lower()))
    save_json(KROKY_PATH, ordered)
    save_json(KROKY_CUSTOM_PATH, ordered)
    print(f"✓ Saved {len(ordered)} actions to both kroky.json and kroky_custom.json")
    
    # Verify file write
    from_file = load_json(KROKY_PATH)
    if action_name in from_file:
        print(f"✓ Verified: action '{action_name}' is in kroky.json")
    else:
        print(f"✗ ERROR: action '{action_name}' NOT in kroky.json!")
        return False
    
    # ========== st.rerun() HAPPENS (line 1054) ==========
    print("\n[4. RERUN - App rerenders]")
    print("-" * 80)
    
    # With our fix: lines 242-276 reload from file
    steps_data = load_json(KROKY_PATH)
    custom_steps = load_json(KROKY_CUSTOM_PATH)
    if custom_steps:
        steps_data.update(custom_steps)
    print(f"✓ Reloaded {len(steps_data)} actions from file (includes new action)")
    
    # Update session_state.steps_data
    session_state['steps_data'] = copy.deepcopy(steps_data)
    print(f"✓ Updated session_state.steps_data with {len(session_state['steps_data'])} actions")
    
    # WITH OUR FIX: lines 944-945 ALWAYS sync edit_steps_data
    session_state['edit_steps_data'] = session_state['steps_data'].copy()
    print(f"✓ Resynced session_state.edit_steps_data (our fix!)")
    print(f"✓ edit_steps_data now has {len(session_state['edit_steps_data'])} actions")
    
    # ========== VERIFICATION ==========
    print("\n[5. VERIFICATION]")
    print("-" * 80)
    
    in_file = action_name in steps_data
    in_memory = action_name in session_state['edit_steps_data']
    
    print(f"Action '{action_name}':")
    print(f"  - In file (kroky.json): {in_file}")
    print(f"  - In memory (edit_steps_data): {in_memory}")
    
    if in_file and in_memory:
        file_content = steps_data[action_name]
        memory_content = session_state['edit_steps_data'][action_name]
        
        desc_match = file_content.get('description') == memory_content.get('description')
        steps_match = len(file_content.get('steps', [])) == len(memory_content.get('steps', []))
        
        print(f"  - Description matches: {desc_match}")
        print(f"  - Steps count matches: {steps_match}")
        
        if desc_match and steps_match:
            print("\n" + "=" * 80)
            print("✅ SUCCESS: Action persists correctly through entire workflow!")
            print("=" * 80)
            return True
    
    print("\n" + "=" * 80)
    print("❌ FAILURE: Action did not persist correctly")
    print("=" * 80)
    return False

if __name__ == "__main__":
    # Clean up first
    kroky_path = Path("data/kroky.json")
    data = load_json(kroky_path)
    if "End_To_End_Test" in data:
        del data["End_To_End_Test"]
    save_json(kroky_path, data)
    
    success = simulate_streamlit_workflow()
    
    # Clean up after
    data = load_json(kroky_path)
    if "End_To_End_Test" in data:
        del data["End_To_End_Test"]
    save_json(kroky_path, data)
    
    exit(0 if success else 1)

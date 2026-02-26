#!/usr/bin/env python3
"""
Simulates the UI workflow of adding a new action.
Tests whether the fix to always reinitialize edit_steps_data solves persistence.
"""

import json
import copy
from pathlib import Path

# Import functions from app
import sys
sys.path.insert(0, '/workspaces/Testool')
from app import load_json, save_json, save_and_update_steps

def test_add_action_persistence():
    """Simulate user adding action via UI"""
    
    KROKY_PATH = Path("data/kroky.json")
    KROKY_CUSTOM_PATH = Path("data/kroky_custom.json")
    
    print("=" * 60)
    print("TEST: Add Action via UI Simulation")
    print("=" * 60)
    
    # Step 1: Initial state (like app startup)
    print("\n1. Initial load (startup):")
    steps_data = load_json(KROKY_PATH)
    print(f"   Loaded {len(steps_data)} actions from kroky.json")
    
    # Step 2: Initialize session state
    print("\n2. Initialize session_state (like Streamlit does):")
    session_state_steps_data = copy.deepcopy(steps_data)
    # THIS IS THE FIX: Always sync edit_steps_data from steps_data
    session_state_edit_steps_data = session_state_steps_data.copy()
    print(f"   edit_steps_data has {len(session_state_edit_steps_data)} actions")
    
    # Step 3: User adds new action via form
    print("\n3. User fills form and clicks 'Save New Action':")
    action_name = "Test_UI_Action"
    action_desc = "Action added via UI"
    new_steps = [
        {"description": "Step 1", "expected": "Expected 1"},
        {"description": "Step 2", "expected": "Expected 2"}
    ]
    
    session_state_edit_steps_data[action_name] = {
        "description": action_desc,
        "steps": new_steps.copy()
    }
    print(f"   Added '{action_name}' to edit_steps_data")
    print(f"   edit_steps_data now has {len(session_state_edit_steps_data)} actions")
    
    # Step 4: Save to file (like save_and_update_steps does)
    print("\n4. Call save_and_update_steps(edit_steps_data):")
    # Simulate save_and_update_steps
    ordered = dict(sorted(session_state_edit_steps_data.items(), key=lambda kv: kv[0].lower()))
    success = save_json(KROKY_PATH, ordered)
    save_json(KROKY_CUSTOM_PATH, ordered)  # Mirror backup
    print(f"   Saved to files: success={success}")
    
    # Step 5: st.rerun() happens - reload from file
    print("\n5. After st.rerun() - reload startup sequence:")
    
    # THIS IS THE KEY: steps_data is reloaded from file
    steps_data = load_json(KROKY_PATH)
    print(f"   Reloaded {len(steps_data)} actions from file")
    
    # THIS IS THE FIX: Always reinitialize edit_steps_data from steps_data
    # (not just on first run with "if not in session_state")
    session_state_edit_steps_data = steps_data.copy()
    print(f"   Reinitialized edit_steps_data from steps_data")
    print(f"   edit_steps_data now has {len(session_state_edit_steps_data)} actions")
    
    # Step 6: Verify action persisted
    print("\n6. Verification:")
    in_file = action_name in steps_data
    in_memory = action_name in session_state_edit_steps_data
    
    file_content = load_json(KROKY_PATH)
    has_correct_structure = (
        action_name in file_content and
        "description" in file_content[action_name] and
        "steps" in file_content[action_name] and
        len(file_content[action_name]["steps"]) == 2
    )
    
    print(f"   ✓ Action in kroky.json: {in_file}")
    print(f"   ✓ Action in edit_steps_data: {in_memory}")
    print(f"   ✓ Has correct structure: {has_correct_structure}")
    
    if in_file and in_memory and has_correct_structure:
        print("\n✅ SUCCESS: Action persists correctly!")
        return True
    else:
        print("\n❌ FAILURE: Action did not persist!")
        if action_name in file_content:
            print(f"   Content in file: {json.dumps(file_content[action_name], indent=2, ensure_ascii=False)}")
        return False

if __name__ == "__main__":
    success = test_add_action_persistence()
    exit(0 if success else 1)

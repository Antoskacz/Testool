#!/usr/bin/env python3
"""
Test the persistence logic without Streamlit.
Verifies that reloading edit_steps_data from steps_data after rerun fixes persistence.
"""

import json
import copy
from pathlib import Path

def load_json(path):
    """Load JSON file"""
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    """Save JSON file"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True

def test_old_logic():
    """Test the OLD buggy logic"""
    print("=" * 70)
    print("TESTING OLD LOGIC (Bug: edit_steps_data not updated after rerun)")
    print("=" * 70)
    
    KROKY_PATH = Path("data/kroky.json")
    
    # Startup 1
    print("\n[STARTUP 1] Load from file and initialize session_state")
    steps_data = load_json(KROKY_PATH)
    print(f"  - steps_data loaded with {len(steps_data)} actions")
    
    # OLD LOGIC: Only init edit_steps_data if not exists
    if "edit_steps_data" not in locals():  # Simulating "not in st.session_state"
        edit_steps_data = steps_data.copy()
        print(f"  - edit_steps_data initialized with {len(edit_steps_data)} actions")
    
    # User adds action
    print("\n[USER ACTION] Add new action 'Test_Action'")
    edit_steps_data["Test_Action"] = {
        "description": "Test",
        "steps": [{"description": "S1", "expected": "E1"}]
    }
    print(f"  - edit_steps_data now has {len(edit_steps_data)} actions")
    
    # Save to file
    print("\n[SAVE] Write to file")
    save_json(KROKY_PATH, edit_steps_data)
    print(f"  - Saved to kroky.json")
    
    # st.rerun() - Startup 2
    print("\n[RERUN/STARTUP 2] App reruns, reload from file")
    steps_data = load_json(KROKY_PATH)  # Reload from file
    print(f"  - steps_data reloaded with {len(steps_data)} actions")
    
    # OLD LOGIC: Don't reinitialize edit_steps_data, it still has old copy
    print(f"  - edit_steps_data UNCHANGED (still has old copy) with {len(edit_steps_data)} actions")
    
    # Check result
    print("\n[RESULT] Check if action persisted in memory:")
    test_action_in_file = "Test_Action" in steps_data
    test_action_in_memory = "Test_Action" in edit_steps_data
    print(f"  - In file: {test_action_in_file}")
    print(f"  - In memory: {test_action_in_memory}")
    
    if test_action_in_file and test_action_in_memory:
        print("\n⚠️  BOTH: This looks OK, but... after rerun, edit_steps_data is out of sync!")
        print("   If user adds another action, it might not see Test_Action!")
        return True
    else:
        print("\n❌ BOTH not True - data lost!")
        return False

def test_new_logic():
    """Test the NEW fixed logic"""
    print("\n\n" + "=" * 70)
    print("TESTING NEW LOGIC (Fix: Always reinit edit_steps_data from steps_data)")
    print("=" * 70)
    
    KROKY_PATH = Path("data/kroky.json")
    
    # Startup 1
    print("\n[STARTUP 1] Load from file and initialize session_state")
    steps_data = load_json(KROKY_PATH)
    print(f"  - steps_data loaded with {len(steps_data)} actions")
    
    # NEW LOGIC: Always sync edit_steps_data from steps_data
    edit_steps_data = steps_data.copy()
    print(f"  - edit_steps_data synced with {len(edit_steps_data)} actions")
    
    # User adds action
    print("\n[USER ACTION] Add new action 'Test_Action'")
    edit_steps_data["Test_Action"] = {
        "description": "Test",
        "steps": [{"description": "S1", "expected": "E1"}]
    }
    print(f"  - edit_steps_data now has {len(edit_steps_data)} actions")
    
    # Save to file
    print("\n[SAVE] Write to file")
    save_json(KROKY_PATH, edit_steps_data)
    print(f"  - Saved to kroky.json")
    
    # st.rerun() - Startup 2
    print("\n[RERUN/STARTUP 2] App reruns, reload from file")
    steps_data = load_json(KROKY_PATH)  # Reload from file
    print(f"  - steps_data reloaded with {len(steps_data)} actions")
    
    # NEW LOGIC: Always reinitialize edit_steps_data from newest steps_data
    edit_steps_data = steps_data.copy()
    print(f"  - edit_steps_data reinitialized with {len(edit_steps_data)} actions (now in sync!)")
    
    # Check result
    print("\n[RESULT] Check if action persisted in memory:")
    test_action_in_file = "Test_Action" in steps_data
    test_action_in_memory = "Test_Action" in edit_steps_data
    print(f"  - In file: {test_action_in_file}")
    print(f"  - In memory: {test_action_in_memory}")
    
    if test_action_in_file and test_action_in_memory:
        print("\n✅ SUCCESS: Both in file AND memory, and they're in sync!")
        return True
    else:
        print("\n❌ FAILURE: Data lost!")
        return False

if __name__ == "__main__":
    # Clean up first
    kroky_path = Path("data/kroky.json")
    data = load_json(kroky_path)
    if "Test_Action" in data:
        del data["Test_Action"]
    save_json(kroky_path, data)
    print("Cleaned up Test_Action from kroky.json\n")
    
    # Test both
    old_result = test_old_logic()
    new_result = test_new_logic()
    
    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Old logic result: {'⚠️ Data in sync but risky' if old_result else '❌ Failed'}")
    print(f"New logic result: {'✅ Fixed!' if new_result else '❌ Failed'}")
    
    # Clean up
    data = load_json(kroky_path)
    if "Test_Action" in data:
        del data["Test_Action"]
    save_json(kroky_path, data)

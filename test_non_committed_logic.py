#!/usr/bin/env python3
"""
Test script to simulate the non-committed actions calculation logic
"""
import json
from pathlib import Path
import copy

# Load actual data from disk
KROKY_PATH = Path('/workspaces/Testool/data/kroky.json')

with open(KROKY_PATH) as f:
    disk_data = json.load(f)

# Simulate session state
session_edit_steps_data = copy.deepcopy(disk_data)

# User adds a new action "test" to session state
print("=" * 60)
print("SIMULATION:添加新  action to edit_steps_data")
print("=" * 60)
session_edit_steps_data["test"] = {
    "description": "Test action for debugging",
    "steps": [
        {"description": "Step 1", "expected": "Expected 1"}
    ]
}

print(f"\nAfter adding 'test' to edit_steps_data:")
print(f"  session_edit_steps_data has 'test'? {('test' in session_edit_steps_data)}")
print(f"  session_edit_steps_data keys: {sorted(session_edit_steps_data.keys())}")

# Simulate save operation
print(f"\n" + "=" * 60)
print("SIMULATE: User saves new action")
print("=" * 60)

# In save_and_update_steps, the data is saved to kroky.json
# For simulation, let's just update disk_data (which would be new kroky.json content)
disk_data["test"] = session_edit_steps_data["test"]

print(f"\nAfter save (disk_data updated):")
print(f"  disk_data has 'test'? {('test' in disk_data)}")
print(f"  disk_data keys: {sorted(disk_data.keys())}")

# Now calculate non_committed CORRECTLY
print(f"\n" + "=" * 60)
print("CORRECT CALCULATION OF NON_COMMITTED")
print("=" * 60)

disk_action_names = set(disk_data.keys()) if disk_data else set()
mem_action_names = set(session_edit_steps_data.keys()) if session_edit_steps_data else set()
non_committed = mem_action_names - disk_action_names

print(f"\ndisk_action_names ({len(disk_action_names)}): {sorted(disk_action_names)}")
print(f"mem_action_names ({len(mem_action_names)}): {sorted(mem_action_names)}")
print(f"non_committed ({len(non_committed)}): {non_committed}")

if "test" in disk_action_names:
    print(f"  -> 'test' is in BOTH disk and memory")
    print(f"  -> non_committed should be EMPTY or 0")
if "test" in mem_action_names and "test" not in disk_action_names:
    print(f"  -> 'test' is in memory but NOT on disk")
    print(f"  -> non_committed should contain 'test' and be > 0")

# Now simulate REFRESH scenario
print(f"\n\n" + "=" * 60)
print("SCENARIO: User refreshes page WITHOUT saving")
print("=" * 60)

# Reset to real disk state (refresh would reload kroky.json without 'test')
with open(KROKY_PATH) as f:
    disk_data_refresh = json.load(f)

# But session state WOULD preserve edit_steps_data with 'test'
session_edit_steps_data_refresh = copy.deepcopy(session_edit_steps_data)

print(f"\nAfter refresh (but 'test' was NOT saved to disk):")
print(f"  Real disk_data has 'test'? {('test' in disk_data_refresh)}")
print(f"  Session edit_steps_data has 'test'? {('test' in session_edit_steps_data_refresh)}")

# Calculate non_committed
disk_action_names_refresh = set(disk_data_refresh.keys()) if disk_data_refresh else set()
mem_action_names_refresh = set(session_edit_steps_data_refresh.keys()) if session_edit_steps_data_refresh else set()
non_committed_refresh = mem_action_names_refresh - disk_action_names_refresh

print(f"\ndisk_action_names ({len(disk_action_names_refresh)}): {sorted(list(disk_action_names_refresh)[:3])}... (truncated)")
print(f"mem_action_names ({len(mem_action_names_refresh)}): {sorted(list(mem_action_names_refresh)[:3])}... (truncated)")
print(f"\nnon_committed = mem - disk:")
print(f"  non_committed count: {len(non_committed_refresh)}")
if "test" in non_committed_refresh:
    print(f"  -> 'test' IS in non_committed ✓ (CORRECT!)")
else:
    print(f"  -> 'test' is NOT in non_committed ✗ (BUG!)")
print(f"\nExpected non_committed count: 1")
print(f"Actual non_committed count: {len(non_committed_refresh)}")
if len(non_committed_refresh) == 1:
    print(f"  -> Calculation is CORRECT ✓")
else:
    print(f"  -> Calculation is WRONG ✗ (BUG!)")

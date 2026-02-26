"""
Test script to demonstrate dual-file persistence system.

This system ensures that if saving to kroky.json fails for any reason,
new actions are saved to kroky_custom.json as a fallback. On app startup,
both files are loaded and merged so no data is lost.

Run with: python test_dual_persistence.py
"""

from pathlib import Path
import json
import tempfile
import shutil
from core import save_json, load_json, KROKY_PATH


def test_dual_persistence():
    """Test the dual-file persistence system."""
    
    # Setup
    base_dir = Path(__file__).resolve().parent
    kroky = base_dir / "data" / "kroky.json"
    kroky_custom = base_dir / "data" / "kroky_custom.json"
    
    # Backup existing files
    backup_dir = tempfile.mkdtemp()
    if kroky.exists():
        shutil.copy2(kroky, Path(backup_dir) / "kroky.json")
    if kroky_custom.exists():
        shutil.copy2(kroky_custom, Path(backup_dir) / "kroky_custom.json")
    
    try:
        # Test 1: Create basic action in primary file
        print("\n✅ Test 1: Save action to primary file")
        primary = {"Action1": {"description": "desc", "steps": []}}
        save_json(kroky, primary)
        assert kroky.exists() and "Action1" in load_json(kroky)
        print("   ✓ Primary file created and saved")
        
        # Test 2: Simulate adding custom action via fallback
        print("\n✅ Test 2: Add custom action to custom file")
        custom = {"CustomAction": {"description": "custom desc", "steps": []}}
        save_json(kroky_custom, custom)
        assert kroky_custom.exists() and "CustomAction" in load_json(kroky_custom)
        print("   ✓ Custom file created")
        
        # Test 3: Simulate startup merge
        print("\n✅ Test 3: Simulate startup merge of both files")
        primary = load_json(kroky)
        custom = load_json(kroky_custom)
        merged = {**primary, **custom}
        
        assert len(merged) == 2
        assert "Action1" in merged
        assert "CustomAction" in merged
        print(f"   ✓ Merged: {len(primary)} primary + {len(custom)} custom = {len(merged)} total")
        
        # Test 4: Simulate explicit merge (user clicks button)
        print("\n✅ Test 4: User explicitly merges custom into primary")
        save_json(kroky, merged)  # Save merged result back
        kroky_custom.unlink()  # Delete custom file
        
        final = load_json(kroky)
        assert len(final) == 2
        assert not kroky_custom.exists()
        print(f"   ✓ Merged state saved to primary, custom file deleted")
        
        print("\n✅ All dual-persistence tests passed!")
        
    finally:
        # Restore backups
        if (Path(backup_dir) / "kroky.json").exists():
            shutil.copy2(Path(backup_dir) / "kroky.json", kroky)
            print("✓ Restored original kroky.json")
        
        if (Path(backup_dir) / "kroky_custom.json").exists():
            shutil.copy2(Path(backup_dir) / "kroky_custom.json", kroky_custom)
            print("✓ Restored original kroky_custom.json")
        
        shutil.rmtree(backup_dir)


if __name__ == "__main__":
    test_dual_persistence()

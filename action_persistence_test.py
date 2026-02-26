"""Simple script to verify kroky.json persistence utilities.

Run with `python action_persistence_test.py` from the workspace root.
"""

from core import load_json, save_json, add_new_action, update_action, delete_action, KROKY_PATH


def main():
    # start with a clean file
    save_json(KROKY_PATH, {})
    assert load_json(KROKY_PATH) == {}

    # add an action
    assert add_new_action("Foo", "desc", [{"description": "a", "expected": "b"}])
    data = load_json(KROKY_PATH)
    assert "Foo" in data
    assert data["Foo"]["description"] == "desc"
    assert data["Foo"]["steps"][0]["description"] == "a"

    # edit the action
    assert update_action(
        "Foo",
        "desc2",
        [{"description": "a2", "expected": "b2"}, {"description": "a3", "expected": "b3"}],
    )
    updated_data = load_json(KROKY_PATH)
    assert updated_data["Foo"]["description"] == "desc2"
    assert len(updated_data["Foo"]["steps"]) == 2

    # ensure scenarios referencing the action pick up the new steps
    def update_scenarios(projects_data, steps_data, action_name):
        updated = 0
        for project_data in projects_data.values():
            if isinstance(project_data, dict) and "scenarios" in project_data:
                for scenario in project_data["scenarios"]:
                    if scenario.get("akce") == action_name:
                        if action_name in steps_data:
                            action_data = steps_data[action_name]
                            if isinstance(action_data, dict) and "steps" in action_data:
                                scenario["kroky"] = action_data["steps"].copy()
                                updated += 1
                            elif isinstance(action_data, list):
                                scenario["kroky"] = action_data.copy()
                                updated += 1
        return updated

    projects = {"p": {"scenarios": [{"akce": "Foo", "kroky": []}]}}
    count = update_scenarios(projects, load_json(KROKY_PATH), "Foo")
    assert count == 1 and len(projects["p"]["scenarios"][0]["kroky"]) == 2

    print("✅ kroky.json persistence utilities working correctly")


if __name__ == "__main__":
    main()

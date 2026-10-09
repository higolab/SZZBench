from szzbench.graph_operations import apply_graph_operation_to_filesystem
from szzbench.graph_simulator import simulate_graph_scenario
from szzbench.graph_validator import validate_graph_static


def test_insert_after_is_validated_and_simulated():
    scenario = {
        "schema_version": "graph-1.0",
        "meta": {
            "id": "SZZG-9001",
            "title": "Insert after smoke",
            "category": "smoke",
            "factors": [],
        },
        "repository": {"name": "insert-after-smoke", "default_branch": "main"},
        "commits": [
            {
                "id": "c0",
                "branch": "main",
                "parents": [],
                "message": "create text file",
                "operations": [
                    {
                        "type": "write_file",
                        "path": "src/example.txt",
                        "content": "alpha\nmarker\nomega\n",
                    }
                ],
            },
            {
                "id": "c1",
                "branch": "main",
                "parents": ["c0"],
                "message": "insert text after marker",
                "operations": [
                    {
                        "type": "insert_after",
                        "path": "src/example.txt",
                        "anchor": "marker\n",
                        "content": "inserted\n",
                    }
                ],
            },
        ],
        "bugs": [
            {
                "id": "B001",
                "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                "bug_fixing_commits": [{"commit": "c1", "role": "complete_fix"}],
            }
        ],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }

    validation = validate_graph_static(scenario, strict_paths=True)
    simulation = simulate_graph_scenario(scenario)

    assert not validation.has_errors()
    assert not simulation.has_errors()


def test_insert_after_updates_filesystem(tmp_path):
    repo_dir = tmp_path / "repo"
    target = repo_dir / "src" / "example.txt"
    target.parent.mkdir(parents=True)
    target.write_text("alpha\nmarker\nomega\n", encoding="utf-8")

    apply_graph_operation_to_filesystem(
        repo_dir,
        {
            "type": "insert_after",
            "path": "src/example.txt",
            "anchor": "marker\n",
            "content": "inserted\n",
        },
    )

    assert target.read_text(encoding="utf-8") == "alpha\nmarker\ninserted\nomega\n"

from pathlib import Path
import json
import subprocess
import sys
import textwrap
import yaml

def _write_classic_scenario(path: Path, scenario_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            schema_version: "1.0"
            meta:
              id: "{scenario_id}"
              title: "Bulk classic smoke"
              category: "smoke"
              factors: []
            repository:
              name: "{scenario_id.lower()}-bulk-classic-smoke"
              default_branch: "main"
              language: "text"
            commits:
              - id: "c0"
                message: "Introduce text bug"
                role: "bug_introducing"
                operations:
                  - type: "write_file"
                    path: "src/example.txt"
                    content: |
                      state=buggy
              - id: "c1"
                message: "Fix text bug"
                role: "bug_fixing"
                operations:
                  - type: "replace"
                    path: "src/example.txt"
                    old: "state=buggy"
                    new: "state=fixed"
            bugs:
              - id: "B001"
                bug_fixing_commit: "c1"
                bug_introducing_commits:
                  - "c0"
                fault:
                  commit: "c0"
                  file: "src/example.txt"
                  statement: "state=buggy"
                  change_type: "line_modification"
                fix:
                  commit: "c1"
                  file: "src/example.txt"
                  statement: "state=fixed"
            """
        ),
        encoding="utf-8",
    )

def _write_graph_scenario(path: Path, scenario_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            schema_version: graph-0.1-draft
            meta:
              id: "{scenario_id}"
              title: "Bulk graph smoke"
              category: "smoke"
              factors: []
            repository:
              name: "{scenario_id.lower()}-bulk-graph-smoke"
              default_branch: main
            commits:
              - id: c0
                branch: main
                parents: []
                message: Introduce graph text bug
                role: bug_introducing
                operations:
                  - type: write_file
                    path: src/example.txt
                    content: |
                      state=buggy
              - id: c1
                branch: main
                parents: [c0]
                message: Fix graph text bug
                role: bug_fixing
                operations:
                  - type: replace
                    path: src/example.txt
                    old: state=buggy
                    new: state=fixed
            bugs:
              - id: B001
                bug_introducing_commits:
                  - commit: c0
                    role: direct
                bug_fixing_commits:
                  - commit: c1
                    role: complete_fix
                faults:
                  - commit: c0
                    file: src/example.txt
                    statement: state=buggy
                fixes:
                  - commit: c1
                    file: src/example.txt
                    statement: state=fixed
            expected_szz:
              commit_level:
                evaluation_policy: exact_set
                required: [c0]
            """
        ),
        encoding="utf-8",
    )

def test_validate_and_generate(tmp_path):
    scenario = Path("examples/basic/simple-line-modification/scenario.yml")
    out = tmp_path / "generated"
    subprocess.run([sys.executable, "-m", "szzbench.cli", "validate", "--simulate", str(scenario)], check=True)
    subprocess.run([sys.executable, "-m", "szzbench.cli", "generate", str(scenario), "--out", str(out), "--force"], check=True)
    assert (out / "repo" / ".git").exists()
    assert (out / "metadata" / "commit-map.json").exists()
    log = subprocess.run(["git", "log", "--oneline"], cwd=out / "repo", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    assert "Initial correct implementation" in log
    assert "Introduce boundary bug" in log
    assert "Fix boundary bug" in log

def test_generate_all_repos_generates_skips_and_overwrites(tmp_path):
    scenarios_root = tmp_path / "scenarios"
    advanced_scenarios_root = tmp_path / "advanced-scenarios"
    output_root = tmp_path / "generated-input-repos"
    _write_classic_scenario(scenarios_root / "SZZ-9000" / "scenario.yml", "SZZ-9000")
    _write_graph_scenario(advanced_scenarios_root / "SZZG-9000" / "scenario.graph.yml", "SZZG-9000")

    base_cmd = [
        sys.executable,
        "-m",
        "szzbench.cli",
        "generate-all-repos",
        "--scenarios-root",
        str(scenarios_root),
        "--advanced-scenarios-root",
        str(advanced_scenarios_root),
        "--out-root",
        str(output_root),
    ]
    first = subprocess.run(base_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert "Generated [classic] SZZ-9000" in first.stdout
    assert "Generated [graph] SZZG-9000" in first.stdout
    assert (output_root / "SZZ-9000" / "default" / "repo" / ".git").exists()
    assert (output_root / "SZZG-9000" / "default" / "repo" / ".git").exists()

    marker = output_root / "SZZ-9000" / "default" / "marker.txt"
    marker.write_text("keep until overwrite\n", encoding="utf-8")
    second = subprocess.run(base_cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert "Skipped [classic] SZZ-9000" in second.stdout
    assert "Skipped [graph] SZZG-9000" in second.stdout
    assert marker.exists()

    third = subprocess.run([*base_cmd, "--overwrite"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert "Overwrote [classic] SZZ-9000" in third.stdout
    assert "Overwrote [graph] SZZG-9000" in third.stdout
    assert not marker.exists()

def test_clean_removes_generated_outputs(tmp_path):
    scenario = Path("examples/basic/simple-line-modification/scenario.yml")
    root = tmp_path / "generated-input-repos"
    out = root / "basic" / "simple-line-modification" / "default"
    out_variant = root / "basic" / "simple-line-modification" / "variant"
    keep = root / "not-generated" / "notes.txt"
    keep.parent.mkdir(parents=True)
    keep.write_text("keep me\n", encoding="utf-8")

    subprocess.run([sys.executable, "-m", "szzbench.cli", "generate", str(scenario), "--out", str(out), "--force"], check=True)
    subprocess.run([sys.executable, "-m", "szzbench.cli", "generate", str(scenario), "--out", str(out_variant), "--force"], check=True)

    dry_run = subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "clean", "--root", str(root), "--dry-run"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert "Would remove:" in dry_run.stdout
    assert out.exists()
    assert out_variant.exists()

    clean = subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "clean", "--root", str(root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    assert "Removed:" in clean.stdout
    assert not out.exists()
    assert not out_variant.exists()
    assert keep.exists()

def test_new_scenario_creates_next_skeleton(tmp_path):
    root = tmp_path / "scenarios"
    root.mkdir()
    (root / "SZZ-0002").mkdir()
    (root / "index.yml").write_text(
        """scenarios:
  - id: "SZZ-0001"
    title: "Existing one"
    path: "scenarios/SZZ-0001/scenario.yml"

  - id: "SZZ-0003"
    title: "Existing three"
    path: "scenarios/SZZ-0003/scenario.yml"
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "szzbench.cli",
            "new-scenario",
            "--root",
            str(root),
            "--title",
            "Formatting after bug introduction",
            "--category",
            "formatting",
            "--factor",
            "formatting-after-bic",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    scenario_dir = root / "SZZ-0004"
    assert "Created" in result.stdout
    assert "Updated" in result.stdout
    assert (scenario_dir / "scenario.yml").exists()
    assert (scenario_dir / "README.md").exists()

    scenario = yaml.safe_load((scenario_dir / "scenario.yml").read_text(encoding="utf-8"))
    assert scenario["meta"]["id"] == "SZZ-0004"
    assert scenario["meta"]["title"] == "Formatting after bug introduction"
    assert scenario["meta"]["slug"] == "formatting-after-bug-introduction"
    assert scenario["meta"]["category"] == "formatting"
    assert scenario["meta"]["factors"] == ["formatting-after-bic"]
    assert scenario["meta"]["status"] == "draft"

    index = yaml.safe_load((root / "index.yml").read_text(encoding="utf-8"))
    assert index["scenarios"][-1]["id"] == "SZZ-0004"
    assert index["scenarios"][-1]["path"].endswith("SZZ-0004/scenario.yml")

def test_graph_apply_patch_from_generates(tmp_path):
    scenario = tmp_path / "scenario.graph.yml"
    scenario.write_text(
        textwrap.dedent(
            """\
            schema_version: graph-0.1-draft
            meta:
              id: SZZG-9998
              title: Apply patch from smoke
              category: smoke
              factors: []
            repository:
              name: graph-apply-patch-from-smoke
              default_branch: main
            commits:
            - id: c0
              branch: main
              parents: []
              message: Initial implementation
              role: initial
              operations:
              - type: write_file
                path: src/main/java/example/Range.java
                content: |
                  package example;
                  public class Range {
                    public boolean contains(int value, int min, int max) {
                      return value >= min && value <= max;
                    }
                  }
            - id: c1
              branch: main
              parents: [c0]
              message: Introduce boundary bug
              role: bug_introducing
              operations:
              - type: replace
                path: src/main/java/example/Range.java
                old: return value >= min && value <= max;
                new: return value > min && value < max;
            - id: c2
              branch: main
              parents: [c1]
              message: Fix boundary bug
              role: bug_fixing
              operations:
              - type: replace
                path: src/main/java/example/Range.java
                old: return value > min && value < max;
                new: return value >= min && value <= max;
            - id: r1
              branch: release
              parents: [c0]
              message: Cherry-pick boundary bug
              role: cherry_pick
              operations:
              - type: apply_patch_from
                commit: c1
            bugs:
            - id: B001
              bug_introducing_commits:
              - commit: c1
                role: direct
              bug_fixing_commits:
              - commit: c2
                role: complete_fix
              faults:
              - id: F001
                commit: c1
                file: src/main/java/example/Range.java
                statement: return value > min && value < max;
              fixes:
              - id: X001
                commit: c2
                file: src/main/java/example/Range.java
                statement: return value >= min && value <= max;
            expected_szz:
              commit_level:
                evaluation_policy: exact_set
                required: [c1]
            """
        ),
        encoding="utf-8",
    )
    out = tmp_path / "generated"

    subprocess.run([sys.executable, "-m", "szzbench.cli", "validate-graph", str(scenario), "--simulate"], check=True)
    subprocess.run([sys.executable, "-m", "szzbench.cli", "generate-graph", str(scenario), "--out", str(out), "--force"], check=True)

    release_content = subprocess.run(
        ["git", "show", "HEAD:src/main/java/example/Range.java"],
        cwd=out / "repo",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    assert "return value > min && value < max;" in release_content

def test_graph_map_records_rebase_of(tmp_path):
    scenario = Path("advanced-scenarios/SZZG-0073/scenario.graph.yml")
    out = tmp_path / "generated"

    subprocess.run([sys.executable, "-m", "szzbench.cli", "generate-graph", str(scenario), "--out", str(out), "--force"], check=True)

    graph_map = json.loads((out / "metadata" / "graph-map.json").read_text(encoding="utf-8"))
    assert graph_map["commits"]["r1"]["rebase_of"] == "f1"
    assert graph_map["commits"]["r2"]["rebase_of"] == "f2"

def test_validate_graph_simulate_reports_operation_state_errors(tmp_path):
    scenario = tmp_path / "scenario.graph.yml"
    scenario.write_text(
        textwrap.dedent(
            """\
            schema_version: graph-0.1-draft
            meta:
              id: SZZG-9999
              title: Broken graph smoke
              category: smoke
              factors: []
            repository:
              name: broken-graph-smoke
              default_branch: main
            commits:
            - id: c0
              branch: main
              parents: []
              message: Initial implementation
              role: initial
              operations:
              - type: write_file
                path: src/main/java/example/Range.java
                content: ok
            - id: c1
              branch: main
              parents: [c0]
              message: Rename missing file
              role: intermediate
              operations:
              - type: rename_file
                from: src/main/java/example/Missing.java
                to: src/main/java/example/Range.java
            bugs:
            - id: B001
              bug_introducing_commits:
              - commit: c0
                role: direct
              bug_fixing_commits:
              - commit: c1
                role: complete_fix
            expected_szz:
              commit_level:
                evaluation_policy: exact_set
                required: [c0]
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "validate-graph", str(scenario), "--simulate"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 1
    assert "rename_file source does not exist" in result.stdout

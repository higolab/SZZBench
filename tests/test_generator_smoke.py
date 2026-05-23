from pathlib import Path
import subprocess
import sys
import yaml

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

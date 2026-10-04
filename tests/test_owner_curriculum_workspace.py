from pathlib import Path


INDEX = Path("frontend/index.html").read_text(encoding="utf-8")
APP = Path("frontend/app.js").read_text(encoding="utf-8")


def test_owner_curriculum_workspace_is_present():
    assert 'id="ownerCurriculumWorkspace"' in INDEX
    assert 'id="curriculumProgramForm"' in INDEX
    assert 'id="curriculumStructure"' in INDEX


def test_workspace_uses_owner_curriculum_api_only():
    assert "jsonRequest('/api/owner/curriculum')" in APP
    assert "jsonRequest('/api/owner/curriculum/programs'" in APP
    assert "/api/learner/" not in "\n".join(
        line for line in APP.splitlines() if "Curriculum" in line or "curriculum" in line
    )


def test_workspace_does_not_add_publish_or_release_controls():
    workspace = INDEX.split('id="ownerCurriculumWorkspace"', 1)[1].split("<hr>", 1)[0].lower()
    assert "publish" in workspace  # explanatory disabled-state notice
    assert ">publish<" not in workspace
    assert "release curriculum" not in workspace


def test_locked_scalp_detection_is_not_added_to_workspace():
    combined = (INDEX + "\n" + APP).lower()
    assert "condition detection" not in combined

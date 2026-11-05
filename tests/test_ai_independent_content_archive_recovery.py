"""Offline synthetic CrownPath website/curriculum archive recovery smoke tests.

Only creates fictional files in tmp_path; no production access or AI services.
"""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_synthetic_website_curriculum_archive_restores_without_ai(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    files = {
        "website/index.html": b"<h1>CrownPath synthetic classroom</h1>",
        "curriculum/scalp-care.md": b"# Synthetic scalp-care lesson\n",
        "curriculum/barber-safety.md": b"# Synthetic barber safety lesson\n",
    }
    for relative, content in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    manifest = {name: checksum(data) for name, data in files.items()}
    archive = tmp_path / "crownpath_synthetic_export.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as zf:
        for name in sorted(files):
            zf.write(source / name, arcname=name)
        zf.writestr("manifest.json", json.dumps(manifest, sort_keys=True))

    restored = tmp_path / "restored"
    restored.mkdir()
    with ZipFile(archive) as zf:
        names = set(zf.namelist())
        assert names == set(files) | {"manifest.json"}
        saved = json.loads(zf.read("manifest.json"))
        for name in sorted(files):
            assert not Path(name).is_absolute()
            assert ".." not in Path(name).parts
            data = zf.read(name)
            assert checksum(data) == saved[name]
            target = restored / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    for name, content in files.items():
        assert (restored / name).read_bytes() == content
    assert (restored / "website/index.html").read_text().startswith("<h1>")


def test_changed_curriculum_fails_archive_checksum(tmp_path):
    original = b"# Synthetic curriculum\n"
    manifest_digest = checksum(original)
    tampered = b"# Changed curriculum\n"
    assert checksum(tampered) != manifest_digest

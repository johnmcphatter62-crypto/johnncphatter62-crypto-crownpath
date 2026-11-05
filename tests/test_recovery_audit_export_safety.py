"""Synthetic recovery audit CSV export allowlist and formula safety tests."""
import csv
import io

import pytest


COLUMNS = ("actor_id", "backup_id", "outcome", "reason_code")


def _safe_cell(value):
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def export_audit_csv(records, max_rows=100):
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or not 1 <= max_rows <= 100:
        raise ValueError("Invalid export row limit")
    if len(records) > max_rows:
        raise ValueError("Audit export exceeds row limit")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(COLUMNS)
    for record in records:
        writer.writerow([_safe_cell(record.get(key, "")) for key in COLUMNS])
    return stream.getvalue()


def test_only_approved_columns_exported():
    output = export_audit_csv([{
        "actor_id": "fictional-owner", "backup_id": "backup-a",
        "outcome": "denied", "reason_code": "missing-approval",
        "password": "fictional-password", "recovery_token": "fictional-token",
    }])
    assert next(csv.reader(io.StringIO(output))) == list(COLUMNS)
    assert "fictional-password" not in output
    assert "fictional-token" not in output


@pytest.mark.parametrize("payload", [
    "=HYPERLINK(\"https://invalid.example\")",
    "+SUM(1,1)",
    "-2+3",
    "@SUM(1,1)",
    "  =1+1",
])
def test_spreadsheet_formula_prefixes_are_escaped(payload):
    output = export_audit_csv([{"actor_id": payload}])
    rows = list(csv.reader(io.StringIO(output)))
    assert rows[1][0].startswith("'")
    assert rows[1][0][1:] == payload


def test_commas_and_newlines_are_quoted_without_extra_rows():
    output = export_audit_csv([{"actor_id": "fictional,owner\nsecond-line"}])
    rows = list(csv.reader(io.StringIO(output)))
    assert len(rows) == 2
    assert rows[1][0] == "fictional,owner\nsecond-line"


def test_excessive_export_rejected():
    with pytest.raises(ValueError, match="exceeds"):
        export_audit_csv([{}] * 101)


def test_invalid_export_limit_rejected():
    with pytest.raises(ValueError, match="Invalid"):
        export_audit_csv([], max_rows=0)

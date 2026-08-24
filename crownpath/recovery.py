def recovery_plan():
    return {
        "database": [
            "Stop writes if data integrity is uncertain.",
            "Preserve logs and audit records.",
            "Restore from the most recent verified backup when required.",
            "Run migration and integrity checks before reopening writes.",
        ],
        "audio": [
            "Mute affected CrownPath audio zone.",
            "Mark offline playback device unavailable.",
            "Do not bypass provider licensing or authentication.",
            "Restore service only after provider/device health is verified.",
        ],
        "security": [
            "Disable affected account or integration.",
            "Rotate exposed secrets outside source control.",
            "Review audit events.",
            "Require owner approval before reactivation.",
        ],
    }

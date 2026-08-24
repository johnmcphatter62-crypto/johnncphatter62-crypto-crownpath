import os

class PandoraBusinessAdapter:
    provider_name = "PANDORA_FOR_BUSINESS"
    default_station = "Boney James"

    def status(self):
        business_reference = os.getenv("CROWNPATH_PANDORA_BUSINESS_REFERENCE")
        return {
            "provider": self.provider_name,
            "preferred_station": self.default_station,
            "configured": bool(business_reference),
            "credentials_stored_in_crownpath": False,
            "mode": "READY_FOR_CONNECTION" if not business_reference else "CONFIGURED",
        }

    def playback_reference(self):
        # CrownPath does not accept or persist the user's Pandora password.
        return os.getenv("CROWNPATH_PANDORA_BUSINESS_REFERENCE")

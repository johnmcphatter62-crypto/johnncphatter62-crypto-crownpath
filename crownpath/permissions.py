ROLE_PERMISSIONS = {
    "OWNER": {
        "dashboard.owner", "academy.view", "academy.manage", "live.view", "live.manage",
        "digital.view", "digital.manage", "inventory.view", "inventory.manage",
        "awareness.view", "regulatory.view", "regulatory.manage", "security.manage",
        "staff.manage", "audit.view", "documents.view", "learners.view", "audio.view", "audio.manage",
    },
    "INSTRUCTOR": {
        "academy.view", "academy.manage_assigned", "live.view", "live.manage_assigned",
        "digital.view", "digital.manage_assigned", "regulatory.view", "inventory.view",
        "audio.view", "documents.view", "learners.view",
    },
    "BARBER": {"academy.view", "live.view", "digital.view", "regulatory.view"},
    "COSMETOLOGY_PRO": {"academy.view", "live.view", "digital.view", "regulatory.view"},
    "HOME_CARE": {"academy.view", "live.view", "digital.view"},
}

def permissions_for_role(role: str):
    return ROLE_PERMISSIONS.get(role.upper(), set())

def has_permission(user: dict, permission: str) -> bool:
    if not user or not user.get("active"):
        return False
    return permission in permissions_for_role(user["role"])

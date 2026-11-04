# CrownPath Device Discovery — Integration Plan

Status: **TEST-ONLY / NOT RELEASED**. This plan does not authorize production deployment or device access.

## Current evidence and limitations

- Synthetic tests in `tests/test_device_discovery_visibility.py` exercise a locally defined filtering function.
- These tests **do not call CrownPath application endpoints**, authenticate real users, scan hardware, or establish that production data is isolated.
- Bluetooth and Wi-Fi discovery, camera and microphone permission flows, and device-to-account binding are **not yet integrated or verified**.
- Device identifiers in synthetic fixtures are invented. Do not use real student or device data in tests.

## Proposed application contract

1. An authenticated learner requests their approved-device list.
2. Server-side authorization resolves the learner identity and school from the verified session, never from client-supplied owner or school fields.
3. A persistent device record has a server-generated ID, school ID, owner ID, transport type, approval state, revocation state, and authorization generation.
4. The server returns only records belonging to the authenticated learner in their school, approved and not revoked, with a supported transport type.
5. Unauthenticated or inactive sessions are denied. A school administrator must use a separately authorized workflow rather than impersonating a learner.
6. The list endpoint does **not** trigger hardware discovery or grant Bluetooth, Wi-Fi, camera, or microphone access.
7. Device reconnection after timeout or revocation requires a new server-side authorization check and fresh consent where appropriate.
8. Logs must avoid raw hardware identifiers, tokens, camera frames, microphone recordings, and other unnecessary sensitive data.

## Required acceptance evidence before release

- Unit tests import the **actual application policy function**, rather than defining a replacement inside test files.
- Authenticated HTTP tests demonstrate tenant and learner isolation, including forged owner/school inputs and inactive sessions.
- Database tests prove that approval and revocation changes affect responses immediately.
- Browser permission tests verify user gestures and denial/revocation behavior on supported platforms.
- Security review covers CSRF, access-control bypass, rate limiting, retention, and audit logging.
- Hardware compatibility tests are performed on approved test devices without real student data.
- Owner explicitly approves any production rollout. **No automatic merge, deployment, or live payments.**

## Next implementation task

Identify the existing CrownPath authentication and persistence interfaces, then introduce a minimal server-side device-list policy with HTTP tests using synthetic records. Do not add real scanning until the acceptance criteria above are satisfied.

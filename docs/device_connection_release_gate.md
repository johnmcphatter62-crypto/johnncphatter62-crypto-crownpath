# CrownPath Device Connection Release Gate

**Status: BLOCKED for real hardware and production release.**

The current device, media-consent, and session tests are isolated synthetic policy checks. They do **not** prove that a browser can pair Bluetooth devices, join Wi-Fi networks, stream a scalp camera, or control operating-system permissions.

## Required before enabling real connections

- [ ] Choose supported device models and document manufacturer protocols and privacy terms.
- [ ] Confirm browser and operating-system support for each capability. Browser camera and microphone access require user permission and an appropriate secure context.
- [ ] Require explicit user action to initiate pairing or media capture; deny silent activation.
- [ ] Bind device authorization to the authenticated user, school, device, session, and capability.
- [ ] Enforce server-side access checks; do not trust browser-supplied ownership or school IDs.
- [ ] Define consent withdrawal, device disconnection, session expiry, and lost-device procedures.
- [ ] Protect video and scalp images in transit and at rest; define retention and deletion.
- [ ] Show a visible camera/microphone active indicator and a clear stop control.
- [ ] Test on actual supported phones, tablets, computers, and representative devices.
- [ ] Test failures: denied permissions, disconnected Wi-Fi, Bluetooth loss, revoked access, and reconnect.
- [ ] Review privacy, accessibility, security logs, and school/learner consent requirements.
- [ ] Obtain explicit Owner approval before merge, deployment, or live device activation.

## Important limits

Wi-Fi connectivity is normally provided by the user's operating system or network; a website does not silently configure the local Wi-Fi connection. Bluetooth availability varies by browser, operating system, device, and hardware profile. A scalp camera is an optical imaging device, not an X-ray machine; do not claim medical diagnosis from camera images.

**Current authorization:** test-only development. No real pairing, media capture, or production activation.

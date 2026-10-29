# Touch keyboard validation

Scope: LockHost, its new keyboard/model, and the lock surface binding in Service.
No authentication service implementation, PAM, boot or display policy changed.

- Eight focused input/host behavior tests passed in tests/touch-keyboard.test.cjs
  (Node runs with explicit file and one worker).
- Directly affected existing tests/locked-board-idle.test.cjs and
  lock/extras/test-service-api.py passed.
- Changed QML and tests/touch-keyboard-runtime.qml parsed successfully.
- Isolated non-locking QML execution with synthetic text passed: component load,
  mixed input, clear-before-submit, busy-input rejection, cover-input rejection,
  modifier reset and blanked-screen input rejection. No real password was used or inspected.
- Fault injection with a malformed keyboard model preserved the lock host and
  existing design submit path in the isolated QML runtime.
- Follow-up code review found both loader-isolation and blanked-input findings
  resolved, with no remaining blocker before user acceptance.
- Keyboard renders at 1440x900 and 900x1440 logical pixels with visible keys,
  masked input feedback and show/hide control.
- The unchanged legacy Split design/PasswordField uses unqualified Color and
  emits Color.lock warnings in the isolated preview. The new keyboard uses an
  explicit Commons alias and rendered correctly. Offscreen preview also reports
  unavailable desktop IPC/Hyprland; it does not instantiate authentication.
- Actual touchscreen unlock, physical keyboard fallback, and failure recovery
  require user acceptance after installation. Passwords must remain private.

Full repository checks run in GitHub, not locally. The existing workflow includes
the new Node test; a QML parsing job was added for GitHub.

Installed into the active user-owned Flight Board plugin on 2026-10-29.
Original plugin backup: ~/.local/state/omarchy/plugin-backups/nickfoy.flight-board-before-touch-20261029-112117.
The install verified original host/service hashes and copied files only while
the session was unlocked. Omarchy shell was restarted successfully.

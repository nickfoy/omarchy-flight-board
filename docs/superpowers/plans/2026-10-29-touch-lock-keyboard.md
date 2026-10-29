# Touch Lock Keyboard Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution.

**Goal:** Unlock the desktop using only the Yoga touchscreens.
**Architecture:** LockHost owns the keyboard inside the existing secure surface;
its current password signals remain the only authentication interface.
**Tech Stack:** QML and JavaScript, existing Quickshell/PAM service.
**Spec:** ../specs/2026-10-29-touch-lock-keyboard-design.md

## Constraints

Preserve Flight Board, boot unlock and Yoga shelf. No passwords in IPC, logs,
subprocesses or persistent state. Scoped local validation, full GitHub checks.

## Tasks

- [x] Add failing tests for character mapping, modifiers, backspace, invalid keys
  and LockHost input gating/submit routing in tests/touch-keyboard.test.cjs.
- [x] Add lock/TouchKeyboardModel.js, lock/TouchKeyboard.qml; wire a Loader and
  guarded handlers into lock/LockHost.qml. Bind availability/default visibility
  from lock/Service.qml only for actual lock surfaces, not appearance previews.
- [x] Run explicit Node test with one worker and parse only changed QML. Run
  affected existing lock idle/API checks. Exercise QML in isolated runtime with
  synthetic text, including failed input/authentication gates and hide/reset.
- [x] Inspect rendered keyboard at Yoga landscape and portrait logical sizes.
- [x] Review the small authentication-adjacent change before deploying. Back up
  originals; guard installed-source equality; install while unlocked and reload.
- [ ] Push feature branch for full GitHub checks. User tests actual touch-only
  unlock; password must never be requested in chat or logged.

Review focus: cover/DPMS hide must block input; authentication must block repeated
submit; alternate auth must switch safely to password; keyboard must not take
physical input focus; missing keyboard component must preserve existing unlock.

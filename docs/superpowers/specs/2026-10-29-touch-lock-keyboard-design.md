# Touch-only desktop unlock

Nick explicitly requested a desktop lock-screen keyboard after physical testing
showed that the existing boot-time unl0kr keyboard does not cover session unlock.
The running lock provider is nickfoy.flight-board, not the disabled stock locker.

Add a small touch keyboard inside the existing WlSessionLockSurface through
LockHost. Keep the Flight Board cover, selected design, physical keyboard and
existing PAM authentication. Automatically show it on eDP-2 (or eDP-1 if eDP-2
is unavailable), with a show/hide button on all lock surfaces. Use English
QWERTY matching the existing Yoga keyboard: upper/lowercase, all printable ASCII
symbols, space, Backspace, Clear and Unlock. Taps update the existing private
password state and existing submitPassword signal. No password IPC, wtype,
subprocess, logging, file storage or network. Disable edits during authentication;
reset Shift/Caps when hidden or input becomes unavailable. Wrong-password recovery
continues through the existing service. Keyboard includes masked feedback so it
remains usable even if it overlaps a design's password field. Physical keyboard
focus must remain on the existing input. A keyboard parsing failure must not
prevent the lock host or physical-keyboard fallback from loading.

Approaches: extending the active Flight Board lock surface preserves the current
workflow and is the chosen implementation. A separate desktop keyboard cannot
reliably be drawn over a secure lock surface and would pass credentials through
the desktop typing helper. Replacing the active locker would discard unrelated
screensaver/appearance behavior. Neither fits the user's preservation requirement.

No PAM, boot/initramfs, packaged Omarchy, shelf-data or display-policy changes.
Source checkout matches the installed Service.qml and LockHost.qml. Deploy only
the tested changed files after backing up and comparing those originals, while
unlocked. Test with synthetic passwords in an isolated non-locking runtime;
Nick performs actual credential entry privately during final acceptance.

Use workstation-scoped local tests only; full checks run in GitHub. Verify key
mapping, upper/lowercase and symbols, UTF-16 backspace, input/authentication gates,
clear-before-submit, empty submission, physical/virtual mixed typing, reset,
invalid keys, layout sizes, pointer and touch controls, and loading failure.

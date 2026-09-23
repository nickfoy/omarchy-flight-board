# Alpha release checklist

Target: `nickfoy/omarchy-flight-board`, personal GitHub account `nickfoy`. Plugin ID: `nickfoy.flight-board`. Release: `0.1.0-alpha.2`. This file records validation of the alpha; current publication results are available from the repository's Actions and Releases pages.

## Candidate prepared

- [x] Approved Flight Board name, listing, board/settings screenshots and motion media; simulated data labelled.
- [x] Root MIT license and preserved upstream/font/data notices, with verified asset origins.
- [x] Boot-image tools and upstream bundled video artwork excluded.
- [x] Setup, restoration, removal, dependencies and Norwegian live coverage documented.
- [x] 32 Python tests, four JavaScript test files, manifest validation and root QML lint passed. Five upstream QProcess type-resolution warnings remain in idle handlers.
- [x] Lock facade and clip-filename checks, 17 safe-path scenarios and injection-pattern checks passed. ShellCheck is configured for hosted CI but unavailable locally.
- [x] Native lock-appearance styling, animation and settings tabs opened, captured and visually reviewed. Corrected the password-idle explanation; no lock design was changed.
- [x] Cleaned candidate installed with a full backup, shell restarted while unlocked, and password PAM/stock idle/Flight Board services verified. Design, unlock animation, password timeout and configuration preserved.
- [x] Earlier live enable/disable/restore/remove/reinstall and real lock/wake/unlock checks passed on this laptop.
- [x] Nick confirmed the repeated shortened idle journey worked as designed. Machine polling confirmed board/secure lock but did not capture sustained screen-off; both observations are recorded.
- [x] Actual Omarchy add/update commands passed in isolated filesystem/network namespaces against a local Git repository. Fresh add, duplicate ID refusal, fast-forward update, no-op update and conflicting-edit preservation passed. Desktop rescan was stubbed; this was not a fresh-desktop authentication test.
- [x] Personal GitHub identity verified; no `nickfoy.flight-board` collision found in the marketplace registry on 22 September 2026. Recheck before submission; this does not reserve the ID.

## Alpha testing limits accepted

Nick chose a laptop-tested alpha because no clean Omarchy machine or VM is available. Clean-machine setup, multi-monitor, suspend, inhibitor interactions, alternative authentication and native/WebKit visual parity remain unverified. The final cleaned package loaded and retained configuration; the earlier user-observed lock cycle predates that packaging cleanup. These limits are disclosed rather than treated as completed tests.

The listing gallery shows the real browser frontend, not the native secure-board renderer. Native lock-appearance captures are internal review evidence, not proof of renderer parity.

## Publication process

1. Create the public repository under `nickfoy` and push the reviewed candidate.
2. Run hosted CI, resolve any failures, and record the final commit.
3. Publish `v0.1.0-alpha.2` as a prerelease with the prepared notes.
4. Submit the public repository for marketplace review with accurate checklist answers.

No stable-release or broad hardware-support claim is made.

## Marketplace review correction

Submission #8251 identified the optional FIDO2 installer as a blocker. Alpha.2 removes it entirely instead of shipping plugin-controlled privileged PAM writes. Existing system PAM files are untouched. The reviewed runtime logic is otherwise unchanged; a comment and release documentation describe the reduced scope.

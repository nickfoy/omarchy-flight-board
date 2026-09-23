# Lifecycle implementation — 22 September 2026

Release identity: `nickfoy.flight-board`. GitHub owner: `nickfoy`. Installed on Nick's development laptop on 22 September 2026; not published.

## Changes

- Root manifest now clones `omarchy.lock`, allowing the host to restore the stock locker on disable/remove and isolate authentication through its private service store.
- Stock `omarchy.idle` stays enabled. The bundled board timer uses its own `flight-board-idle` IPC target and shares the existing Stay Awake state.
- Both idle lock paths preserve the secure board when the automatic screensaver is active.
- Explicit setup uses the saved board timing, suppresses the stock terminal saver by scheduling it after the fallback lock deadline, and records the two original idle values. No boot hooks, separate plugins, or launcher symlinks are installed.
- Setup/restoration are available in Screensaver settings and through `install.py plan|enable|restore`. Setup refuses a locked session, conflicting provider, missing dependency, or unknown integration record.
- Writes use backups, atomic replacement, optimistic concurrency checks, and rollback. Restore uses compare-and-restore per owned timing key, preserving later user edits. A rollback conflict reports the backup instead of overwriting the newer file.
- Saving board preferences while the plugin is disabled does not re-enable it.
- `install.py` no longer relocates personal project directories, archives other plugins, or removes an entire idle configuration section.
- Added a CI workflow for Python and JavaScript checks. CI has not run remotely.

## Verification completed

- Nick reported on 22 September 2026: "I tested lock and wake and they look good." Recorded as a user-reported pass for lock/wake on the installed personal build. The plugin registry still shows `nick.flight-board` enabled; `nickfoy.flight-board` is not installed. This does not yet validate the release checkout's revised lifecycle or establish that the full 5/7/20-minute sequence was tested.
- 32 Python tests passed: data/cache/timing, setup planning, restoration, partial writes, verification failure, concurrent edits, symlink refusal, disabled-plugin saves, and HTTP origin/session checks.
- Three JavaScript test files passed, including a sandboxed test of the installed Omarchy registry's actual enable/disable functions. It confirms stock lock restoration and stock idle retention without touching the running shell.
- Manifest validation passed.
- QML lint exited 0. Five existing Quickshell `QProcess::ExitStatus` type-resolution warnings remain in idle process handlers.
- JavaScript and Bash syntax checks passed.
- An isolated browser session with temporary config/state/cache displayed the new setup controls. Enabling from that uninstalled checkout correctly refused setup before any desktop changes. The settings layout was visually inspected. Test server stopped afterwards.

## Live laptop verification — 22 September 2026

User authorized deployment and testing. Backups and detailed observations are stored locally under `~/.local/state/flight-board/backups/release-migration-20260922-071558/` (private user configuration; do not publish that directory).

- Restored and verified the stock lock/idle baseline before installing the release build.
- Public setup enabled `nickfoy.flight-board` and verified password PAM, the stock idle service, and the board timer service.
- Ordinary disable restored the stock locker; re-enable preserved board preferences and lock appearance.
- Explicit restoration recovered the original 300/420-second idle values.
- Ordinary removal restored the stock locker and retained the stock idle service.
- Reinstallation and setup succeeded. Final saved schedule remains the user's current **5 / 7 / 60 minutes**, including the user's later screen-off adjustment.
- Fixed loss of lock appearance across explicit restoration/re-enable; the ownership record now retains the plugin entry. Added a regression test.
- A real secure-board test reported `secure=true` after 1.1 seconds with the board visible. The board was dismissed at 7.3 seconds; the display blanked at 22.7 seconds, woke at 31.9 seconds while still secure, and the user unlocked successfully at 40.2 seconds. Authentication was performed by the user.
- Nick confirmed after this test that the board remained visible, the display turned off, and wake presented the password screen for normal unlock.
- Because the cover was dismissed before the requested 15-second board deadline, this run verifies lock/display-off/wake/unlock but **does not verify an uninterrupted board-deadline transition**. The full saved 5/7/60-minute idle cycle was not run.

## Remaining release gates and limits

- Live enable, disable, restore, removal, and reinstall passed on Nick's laptop. A separate clean-machine installation and an actual upstream Git update remain to be tested.
- Verify the full idle → board → session lock → display off → wake → password journey, including inhibitors, suspend, monitor changes, failures, and native/WebKit visual parity.
- Ordinary host disable/remove restores the locker but retains fallback timing; full restoration should be run before removal to recover the old terminal-screensaver schedule. Restart after provider changes to avoid the host's transient IPC ownership collision.
- Stock fallback timing follows compositor idle. Launching the board may count as activity; the bundled board cycle owns the intended 5/7/20 schedule. Hardware verification must confirm this interaction.
- The host does not join this package's file lock. Optimistic comparisons detect intervening edits before writes and during rollback, but cannot provide a cross-process transaction with unrelated shell configuration writers. Avoid simultaneous settings changes during setup.
- Interrupted multi-file setup can leave applied timing with a partial record; backups retain original bytes. The stock idle service stays enabled, and the host knows which lock service to restore. Test interruption recovery on a disposable session before release.
- Nick's personal build was migrated with an explicit backup and a verified stock-service baseline. This one-off migration is not part of public setup. Existing launchers and the compatibility project symlink now resolve to the release build; the old installed package is archived.
- Licensing, asset scope and listing media were completed in the release checkout during the later package review below.

## Password-screen idle return fix — 22 September 2026

The password screen previously used the bundled lock's 15-second timeout to blank the display. It now returns to the secure board at that timeout. The independent screen-off deadline survives cover changes; input starts a fresh full screen-off interval, while returning to the board does not extend it. Manual locks participate when Flight Board integration is enabled. In-flight password authentication is preserved, and partially typed text is cleared before the board reappears.

Deployed with a backup while unlocked and verified with a real manual lock: after **15.5 seconds**, status reported `boardCoverVisible=true`, `secure=true`, `locked=true`, and `screenBlanked=false`. The deadline was unchanged across the password-to-board transition. No unlock was automated. The user's current **1 / 2 / 3-minute** test settings were preserved.

Six regression scenarios exercise the actual lock-service methods: idle return, activity/deadline reset, deadline blanking, authentication in flight, integration disabled, and wake followed by inactivity. All four JavaScript test files pass. Root QML lint and manifest validation pass; direct bundled-service lint retains upstream import/type warnings.


## Repeat shortened idle test — 22 September 2026

Nick requested another test with shortened timings. The installed plugin temporarily used **1 / 2 / 3 minutes**. Monitoring confirmed the desktop board at approximately 60 seconds and the secure board at approximately 121 seconds. At approximately 180 seconds, the cover changed state, but polling did not observe a sustained display-off state: `screenBlanked` remained false in the sampled status and monitor `dpmsStatus` remained true. This telemetry alone neither confirms the intended display-off transition nor establishes a defect.

After the repeat test, Nick reported: **“done, it worked as designed.”** Record this as a user-observed pass of the requested idle/display-off/wake journey on this laptop, separately from the limited machine observations. No speculative lock or pointer behavior change was made from the monitoring discrepancy. The earlier characterization of the telemetry as a confirmed bug was withdrawn.

Temporary timing changes were restored using compare-and-restore. The saved and active schedule was verified as **5 minutes screensaver / 8 minutes lock / 60 minutes display off** (300 / 480 / 3600 seconds). These are Nick's current preferences, distinct from the shipped 5 / 7 / 20 defaults. Private raw logs remain outside the repository.

## Release package review — 22 September 2026

Prepared a root MIT license, preserved upstream MIT notices, added Nerd Fonts notices, verified the bundled font hash and airport-name provenance, and documented assets in `THIRD_PARTY.md`. Removed boot-image/Plymouth helpers and upstream Storm/Eyes/River video artwork from the release checkout. Lock appearance remains included; boot actions are unavailable. The installed plugin was not replaced with this cleaned checkout, so the live test above validates the installed build, not these subsequent packaging changes.

Validation of the release checkout: 32 Python tests and all four JavaScript test files passed, manifest validation and root-service QML lint passed, and the lock UI/service facade check passed (74 used members, 98 declared). The adapted Explorer component compiled successfully with Quickshell's Wayland backend (`Component.Ready`); the offscreen backend cannot compile `PanelWindow`. This was compilation only, not a visual inspection or an authentication test. No window was opened and no lock service was instantiated by that probe.

Remaining: visual inspection and live validation of the final cleaned package, a clean-machine install, a real plugin Git update, hosted CI, permanent ID availability and publication review. Current gallery images capture the browser frontend; native renderer parity, multi-monitor, suspend and inhibitor behavior remain unverified.


## Final candidate validation — 22 September 2026

The adapted Explorer was instantiated on the actual Wayland desktop without a lock service. Styling, animation and settings tabs rendered and were captured and visually reviewed. The password-idle hint was corrected to describe returning to the secure board; Never is documented as overriding display-off. No design or authentication preference was changed by the preview.

All 32 Python tests, four JavaScript files, lock-facade and clip-filename checks, 17 safe-path scenarios and injection-pattern checks passed. Root QML lint passed with five existing QProcess type-resolution warnings in idle handlers. ShellCheck is not installed locally; the root hosted workflow now includes it and the inherited lock checks.

Real Omarchy add/update commands were exercised against a temporary local Git origin, with the actual HOME value unchanged and its config path isolated by mounts. Desktop IPC was hidden and only the rescan call was stubbed. Fresh add, duplicate refusal, real fetch/fast-forward, repeat update and conflicting local edit preservation passed. These results validate the CLI/Git path, not fresh-machine authentication.

The cleaned candidate was installed with a full backup and automatic rollback protection while unlocked. Restart verification confirmed the Flight Board password-PAM provider and stock idle service. Split design, fade transition, 15-second password timeout and saved 5/8/60 schedule were preserved; shell settings, board preferences and integration record were byte-identical. Boot compatibility reports stock and performs no boot-image work. Private deployment evidence is retained outside the repository.

Nick explicitly chose a laptop-tested alpha without a clean-machine environment. Fresh-machine, multi-monitor, suspend, inhibitor and alternative-authentication checks remain disclosed limitations. No additional lock cycle or user authentication was automated.

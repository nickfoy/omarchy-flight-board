# Flight Board lock appearance

This directory contains the lock implementation bundled with Flight Board. It is adapted from [Lock Screen Explorer 1.7.7](https://github.com/SirJul1337/omarchy-lock-explorer) by SirJul1337, with its [MIT license](LICENSE) retained. Omarchy-derived code retains the [Omarchy notice](OMARCHY-LICENSE).

Open Flight Board's **Settings → Screensaver → Lock screen appearance** to choose a design, avatar, unlock transition and password-screen idle timeout. A separate lock plugin is not needed. Authentication remains inside Omarchy's private lock service; the appearance editor receives a restricted facade.

Flight Board adds `BoardFeed.qml`, `BoardOverlay.qml` and `FlapCell.qml`, plus the secure-cover and screen-off scheduling in `Service.qml`. Its top-level plugin retains stock idle as a fallback. Refer to [the project README](../README.md) for setup, timing, restoration and removal.

## Scope of this bundle

- Built-in styling, procedural animations, the visual designer and user-provided clips remain available.
- Plymouth, boot-image editing, boot rotation and the upstream bundled video artwork are excluded. Dormant compatibility properties in the adapted editor return neutral values; the service has no boot-writing processes or helpers.
- Existing custom files under `~/.config/omarchy/lock-designs`, `lock-components` and `lock-videos` remain user-owned. Removing Flight Board does not delete them or revert an independently installed boot theme.
- User-provided video features require `qt6-multimedia`. Weather uses `wttr.in`; music uses local MPRIS. These optional appearance features are not required by the flight board.
- Optional FIDO2 setup in `extras/setup-fido2.sh` installs a dedicated PAM file with administrator approval. Flight Board setup never runs it. Standard password PAM is required and is the tested authentication path.
- Menu/launcher additions are optional appearance-editor actions, separate from Flight Board setup.

Only the tested capabilities documented in Flight Board's README are advertised. Do not follow installation commands from the upstream repository for this bundled copy.

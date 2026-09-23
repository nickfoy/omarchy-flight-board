# Changelog

## 0.1.0-alpha.2 — 22 September 2026

- Removed the optional upstream FIDO2 PAM installer after marketplace review identified a privilege-boundary issue in its use of checkout-controlled PAM content. This package contains no PAM installation/removal helper.
- Existing system-managed authentication configuration is left untouched. The tested password login and flight-board behavior are unchanged.
- Supersedes alpha.1; do not run the optional FIDO2 helper from that earlier version.

## 0.1.0-alpha.1 — 22 September 2026

- Split-flap flight board with Norwegian Avinor arrivals and departures, configurable airports, palettes, rows and time zones.
- Optional 30-second constant turning independent of provider refreshes; expired flights leave the board between fetches.
- Unified screensaver, secure lock cover and display-off settings, with explicit setup/restoration and configuration backups.
- Board returns when the password screen becomes idle while the session remains locked.
- Status heading and consistent A/D tile colours.
- Bundled lock appearance editor; no separate lock plugin installation required.
- MIT project license and third-party notices. Boot-image helpers and upstream video artwork excluded from the release package.
- Actual demo screenshots, a mid-flip frame and animation recording for the listing.

This is a laptop-tested prerelease. See the release checklist for tested behavior and remaining validation limits.

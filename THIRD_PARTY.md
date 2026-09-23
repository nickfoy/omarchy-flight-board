# Third-party notices

Flight Board's original code and listing materials are licensed under the root [MIT license](LICENSE), copyright 2026 nickfoy. The components below retain their respective licenses and notices.

## Omarchy

`IdleModel.js`, `IdleService.qml` and portions of the bundled lock implementation derive from Omarchy by David Heinemeier Hansson and contributors. MIT notice: [lock/OMARCHY-LICENSE](lock/OMARCHY-LICENSE). Source: <https://github.com/omacom/omarchy>.

## Lock Screen Explorer

The `lock/` appearance and authentication implementation is adapted from Lock Screen Explorer 1.7.7 by SirJul1337. Its original MIT notice is retained in [lock/LICENSE](lock/LICENSE). Source: <https://github.com/SirJul1337/omarchy-lock-explorer>.

Flight Board adds the native flight cover and idle/display integration. The release package excludes upstream Plymouth/boot-image helpers and the Storm, Eyes and River videos/designs. Those video assets are not covered by Flight Board's project license and are not redistributed. Existing user-installed boot themes and user videos are not removed by this package.

## Board font

`app/static/board-font.ttf` is JetBrainsMono Nerd Font Bold from the installed Arch package `ttf-jetbrains-mono-nerd-basic 3.5.1-1`. Its SHA-256 is `e490660ad75e0b152c93b1604c2ea1a4ea675f1b8a3fe0d005b1998568f99f1f`, identical to the package's `JetBrainsMonoNerdFont-Bold.ttf`. The file was renamed for the application; the font data is unmodified.

The JetBrains Mono and Nerd Fonts notices are included in [font-license.txt](app/data/font-license.txt) and [nerd-fonts-license.txt](app/data/nerd-fonts-license.txt). The font remains under SIL Open Font License 1.1, separate from the application MIT license.

Sources: [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono), [Nerd Fonts 3.5.1 licensing](https://github.com/ryanoasis/nerd-fonts/blob/v3.5.1/LICENSE).

## Airport names and flight data

`app/data/airports.json` contains 2,021 airport code/name pairs from Avinor's `https://asrv.avinor.no/airportNames/v1.0` service. Its entries were compared with the saved source XML during release preparation on 22 September 2026 and matched exactly. These worldwide names support lookup; live flight coverage is limited to the supported Norwegian Avinor airports.

Runtime flight information comes from `https://asrv.avinor.no/XmlFeed/v1.0`. Avinor data is supplied under [Avinor's terms of use](https://partner.avinor.no/en/services/flight-data/), not the application's MIT license. Keep the visible “Flydata fra Avinor” attribution with the board. The web view links it to Avinor; the secure lock surface displays the attribution without launching a browser over the lock.

The server caches responses and spaces requests for each airport at least three minutes apart. Avinor does not guarantee completeness, timeliness or availability. Demo flights are generated locally and labelled as simulated.

## Listing media

The root `preview.png` and files under `docs/media/` are captures of Flight Board's own shipped web interface and an HTML composition around those captures. They use simulated flights, the bundled font and application UI, with no third-party photographs, airline logos, stock illustrations or sound recordings. They were captured in Chromium at 1920 × 1080 using an isolated demo profile; they do not claim to show the native QML lock renderer.

'use strict';
function timingError(settings) {
  var keys = ['screensaverMinutes', 'lockMinutes', 'screenOffMinutes'];
  for (var i = 0; i < keys.length; i++) {
    var value = settings[keys[i]];
    if (!Number.isInteger(value) || value < 1 || value > 240) return 'Use whole minutes from 1 to 240.';
  }
  if (settings.screensaverMinutes >= settings.lockMinutes || settings.lockMinutes >= settings.screenOffMinutes)
    return 'Choose screensaver first, then lock, then screen off.';
  return '';
}
if (typeof module !== 'undefined') module.exports = {timingError};

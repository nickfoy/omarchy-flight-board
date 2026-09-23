import QtQuick
import Quickshell
import "lock" as Lock

Item {
  id: root
  property var shell: null
  property var manifest: null
  property string omarchyPath: ''
  readonly property string pluginId: manifest && manifest.id ? manifest.id : 'nickfoy.flight-board'
  Lock.Explorer { id: appearance; shell: root.shell; manifest: root.manifest; omarchyPath: root.omarchyPath }
  function open(payloadJson) {
    var payload = {}
    try { payload = JSON.parse(payloadJson || '{}') } catch (error) {}
    if (payload.page === 'lock') { appearance.open('{}'); return }
    Quickshell.execDetached(['/usr/bin/python', decodeURIComponent(String(Qt.resolvedUrl('app/launch.py')).replace(/^file:\/\//, '')), '--settings'])
    if (shell) Qt.callLater(function() { shell.hide(root.pluginId) })
  }
  function close() { appearance.close() }
  function toggle() { open('{}') }
}

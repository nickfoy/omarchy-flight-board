import QtQuick
import Quickshell
import Quickshell.Io
import "lock" as Lock

// The lock-clone host keeps authentication private. Stock idle stays enabled
// for the bar's Stay Awake controls and a fallback lock deadline.
Lock.Service {
  id: root
  property bool integrationReady: false
  property int fallbackLockSeconds: -1
  idleBoardActive: idle.screensaverStartedThisCycle && idle.screensaverWindowCount > 0
  idleBoardBlankMs: (idle.screenOffTimeoutSeconds - idle.lockTimeoutSeconds) * 1000
  lockedBoardEnabled: root.integrationReady
  lockedBoardScreenOffMs: idle.screenOffTimeoutSeconds * 1000

  FileView {
    path: (Quickshell.env('XDG_STATE_HOME') || Quickshell.env('HOME') + '/.local/state') + '/flight-board/integration.json'
    blockLoading: true
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoadFailed: root.integrationReady = false
    onLoaded: {
      try {
        var state = JSON.parse(text())
        root.fallbackLockSeconds = state.appliedIdle ? state.appliedIdle.lock : -1
        root.integrationReady = state.active === true && state.plugin === 'nickfoy.flight-board'
      } catch (error) { root.integrationReady = false }
    }
  }
  IdleService {
    id: idle
    shell: root.shell
    serviceReady: root.integrationReady && root.passwordPamConfigured && root.fallbackLockSeconds === idle.lockTimeoutSeconds
  }
}

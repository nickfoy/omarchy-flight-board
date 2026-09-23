import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: feed
  property bool active: false
  property var config: ({rows: 14, background: '#10120f', grid: '#282b25', letters: '#efc477', mode: 'both', timezone: 'local', constantTurning: false})
  property var flights: []
  property bool stale: false
  property bool received: false
  property string notice: ''
  signal replay()
  onActiveChanged: { retry.stop(); reader.running = active }
  Component.onCompleted: if (active) reader.running = true
  Process {
    id: reader
    command: ['/usr/bin/python', decodeURIComponent(String(Qt.resolvedUrl('../app/lock_feed.py')).replace(/^file:\/\//, ''))]
    stdout: SplitParser {
      onRead: function(line) {
        try {
          var packet = JSON.parse(line)
          feed.config = packet.config
          var flights = []
          var stale = false
          for (var i = 0; i < packet.feeds.length; i++) {
            var item = packet.feeds[i]
            flights = flights.concat(item.flights || [])
            if (item.error || !item.fetchedAt || Date.now() / 1000 - item.fetchedAt > Math.max(180, feed.config.refreshMinutes * 60) * 2) stale = true
          }
          feed.flights = flights
          feed.stale = stale
          feed.received = true
          feed.notice = feed.config.demo ? 'DEMO · SIMULATED FLIGHTS' : stale ? 'STALE DATA · RETRYING' : ''
        } catch (error) { console.warn('Split-Flap lock feed:', error) }
      }
    }
    onExited: if (feed.active) retry.restart()
  }
  Timer { id: retry; interval: 5000; onTriggered: if (feed.active) reader.running = true }
  Timer { interval: 30000; running: feed.active && feed.config.constantTurning === true; repeat: true; onTriggered: feed.replay() }
}

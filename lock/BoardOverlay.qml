import QtQuick
import Quickshell

FocusScope {
  id: board
  required property var feed
  signal revealRequested()
  property var visibleFlights: []
  property var columns: [ ['TIME', 5], ['AIRPORT', 3], ['A / D', 3], ['FLIGHT', 7], ['FROM / TO', 18], ['GATE', 4], ['STATUS', 10] ]
  readonly property var config: feed.config
  readonly property int rowCount: config.rows || 14
  readonly property real groupGap: width < 750 ? 7 : 17
  readonly property real cellGap: width < 550 ? 1 : width < 750 ? 2 : 3
  readonly property real cellWidth: Math.max(1, (grid.width - groupGap * 6 - cellGap * 43) / 50)
  readonly property real cellHeight: Math.max(12, (grid.height - 5 * (rowCount - 1)) / rowCount)
  readonly property real letterSize: Math.max(7, Math.min(cellWidth * 1.6, cellHeight * 0.62))
  FontLoader { id: boardFont; source: Qt.resolvedUrl('../app/static/board-font.ttf') }
  function updateFlights() {
    var now = Date.now()
    visibleFlights = feed.flights.filter(function(f) {
      if (config.mode === 'arrivals' && f.direction !== 'A' || config.mode === 'departures' && f.direction !== 'D') return false
      return Date.parse(f.estimated) > now
    }).sort(function(a, b) { return Date.parse(a.estimated) - Date.parse(b.estimated) }).slice(0, rowCount)
  }
  function clean(value) {
    return String(value || '').toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/Ø/g, 'O').replace(/Æ/g, 'AE').replace(/[^ A-Z0-9:/-]/g, ' ')
  }
  function values(f) {
    if (!f) return ['', '', '', '', '', '', '']
    var time = f.boardTime || ""
    return [time, f.airport, f.direction === 'A' ? 'ARR' : 'DEP', f.flight, f.destination, f.gate || '', f.status]
  }
  function reveal() { board.revealRequested() }
  Keys.onPressed: function(event) { event.accepted = true; reveal() }
  Rectangle { anchors.fill: parent; color: board.config.background || '#10120f' }
  Item {
    id: frame
    anchors.fill: parent
    anchors.leftMargin: board.width < 600 ? 16 : board.width < 950 ? 25 : 49
    anchors.rightMargin: anchors.leftMargin
    Row {
      height: 38
      spacing: board.groupGap
      Repeater {
        model: board.columns
        Text {
          required property var modelData
          width: board.cellWidth * modelData[1] + board.cellGap * (modelData[1] - 1)
          height: 38
          verticalAlignment: Text.AlignVCenter
          text: modelData[0]
          color: '#929989'
          font.family: boardFont.name
          font.pixelSize: board.width < 950 ? 7 : 9
          clip: true
        }
      }
    }
    Column {
      id: grid
      anchors.fill: parent
      anchors.topMargin: 38
      anchors.bottomMargin: 13
      spacing: 5
      Repeater {
        model: board.rowCount
        Row {
          id: flightRow
          required property int index
          readonly property var values: board.values(board.visibleFlights[index])
          height: board.cellHeight
          spacing: board.groupGap
          Repeater {
            model: board.columns
            Row {
              id: group
              required property var modelData
              required property int index
              readonly property string value: board.clean(flightRow.values[index]).padEnd(modelData[1], ' ')
              spacing: board.cellGap
              Repeater {
                model: group.modelData[1]
                FlapCell {
                  id: cellDelegate
                  required property int index
                  width: board.cellWidth
                  height: board.cellHeight
                  target: group.value.charAt(index)
                  color: board.config.grid || '#282b25'
                  letterColor: board.config.letters || '#efc477'
                  letterSize: board.letterSize
                  fontFamily: boardFont.name
                  delay: flightRow.index * 32 + (group.index * 7 + index) * 7
                  Connections { target: board.feed; function onReplay() { cellDelegate.flip() } }
                }
              }
            }
          }
        }
      }
    }
  }
  Text {
    anchors.centerIn: parent
    visible: board.visibleFlights.length === 0
    text: board.feed.received ? 'A quiet moment on the runway' : 'Connecting to the runway…'
    color: board.config.letters || '#efc477'
    font.pixelSize: 20
  }
  Text {
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.rightMargin: 50
    text: (board.feed.notice ? board.feed.notice + ' · ' : '') + 'Flydata fra Avinor'
    color: '#969d8e'
    font.pixelSize: 8
  }
  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.BlankCursor
    property real initialX: -1
    property real initialY: -1
    onPressed: board.reveal()
    onWheel: function(wheel) { wheel.accepted = true; board.reveal() }
    onPositionChanged: function(mouse) {
      if (initialX < 0) { initialX = mouse.x; initialY = mouse.y; return }
      if (Math.hypot(mouse.x - initialX, mouse.y - initialY) > 12) board.reveal()
    }
  }
  Timer { interval: 15000; running: board.visible; repeat: true; onTriggered: board.updateFlights() }
  Connections { target: board.feed; function onFlightsChanged() { board.updateFlights() } function onConfigChanged() { board.updateFlights() } }
  Component.onCompleted: { updateFlights(); forceActiveFocus() }
}

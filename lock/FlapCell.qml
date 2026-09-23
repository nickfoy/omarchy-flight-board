import QtQuick
Rectangle {
  id: cell
  property string target: ' '
  property color letterColor: '#efc477'
  property real letterSize: 24
  property string fontFamily: 'monospace'
  property int delay: 0
  property string displayed: ' '
  property int steps: 0
  property int step: 0
  property string alphabet: ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:/-'
  radius: 2
  color: '#282b25'
  clip: true
  function flip() {
    step = 0
    steps = 3 + Math.floor(Math.random() * 3)
    tick.stop()
    start.restart()
  }
  onTargetChanged: flip()
  Timer { id: start; interval: cell.delay; onTriggered: { cell.advance(); tick.start() } }
  Timer { id: tick; interval: 185; repeat: true; onTriggered: cell.advance() }
  function advance() {
    step++
    displayed = step >= steps ? target : alphabet[(Math.max(0, alphabet.indexOf(displayed)) + 3 + step * 2) % alphabet.length]
    swing.restart()
    if (step >= steps) tick.stop()
  }
  Text {
    id: glyph
    anchors.centerIn: parent
    text: cell.displayed
    color: cell.letterColor
    font.family: cell.fontFamily
    font.pixelSize: cell.letterSize
    transform: Scale { id: squash; origin.x: glyph.width / 2; origin.y: glyph.height / 2; yScale: 1 }
  }
  SequentialAnimation {
    id: swing
    NumberAnimation { target: squash; property: 'yScale'; from: 0.1; to: 1; duration: 170; easing.type: Easing.OutQuad }
  }
  Rectangle { width: parent.width; height: 1; anchors.verticalCenter: parent.verticalCenter; color: '#10120f' }
}

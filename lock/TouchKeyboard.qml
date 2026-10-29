import QtQuick
import qs.Commons
import qs.Commons as Commons
import "TouchKeyboardModel.js" as KeyboardModel

Rectangle {
  id: keyboard
  Commons.Translations {id: strings; directory: Qt.resolvedUrl("i18n")}
  property bool shift: false
  property bool caps: false
  property int characterCount: 0
  property string failureMessage: ""
  property bool authenticating: false
  signal keyRequested(string code)
  function applyKey(text, code, shift, caps) {
    return KeyboardModel.applyKey(text, code, shift, caps)
  }
  implicitHeight: 330
  radius: Style.cornerRadius
  color: Commons.Color.background
  border.color: Commons.Color.lock.borderActive
  border.width: 1

  Column {
    anchors.fill: parent
    anchors.margins: 12
    spacing: 8
    Text {
      width: parent.width
      height: 32
      textFormat: Text.PlainText
      text: keyboard.authenticating ? strings.t("keyboard.checking") : keyboard.failureMessage.length ? keyboard.failureMessage
        : keyboard.characterCount ? "●".repeat(Math.min(keyboard.characterCount,32)) : strings.t("keyboard.prompt")
      color: keyboard.failureMessage.length ? Commons.Color.lock.textError : Commons.Color.lock.text
      font.family: Style.font.family
      font.pixelSize: 20
      horizontalAlignment: Text.AlignHCenter
      verticalAlignment: Text.AlignVCenter
      elide: Text.ElideRight
    }
    Repeater {
      model: KeyboardModel.rows()
      Row {
        id: keyRow
        required property var modelData
        width: parent.width
        height: (keyboard.height-24-32-40)/5
        spacing: 6
        readonly property real units: modelData.reduce(function(sum,k){return sum+k.units},0)
        Repeater {
          model: keyRow.modelData
          Rectangle {
            id: keycap
            required property var modelData
            readonly property bool selected: modelData.code === "Shift" ? keyboard.shift : modelData.code === "Caps" && keyboard.caps
            width: (keyRow.width-(keyRow.modelData.length-1)*keyRow.spacing)*modelData.units/keyRow.units
            height: keyRow.height
            radius: Style.cornerRadius
            color: tap.pressed || selected ? Commons.Color.accent : Qt.lighter(Commons.Color.background,1.4)
            border.width: 1
            border.color: Commons.Color.lock.borderActive
            opacity: keyboard.enabled ? 1 : .5
            Accessible.role: Accessible.Button
            Accessible.name: modelData.code.length > 1 && modelData.code !== "Backspace" ? strings.t("keyboard."+modelData.code) : modelData.code
            Text {
              anchors.fill: parent
              textFormat: Text.PlainText
              text: keycap.modelData.code.length > 1 && keycap.modelData.code !== "Backspace"
                ? strings.t("keyboard."+keycap.modelData.code) : KeyboardModel.label(keycap.modelData,keyboard.shift,keyboard.caps)
              color: tap.pressed || keycap.selected ? Commons.Color.background : Commons.Color.foreground
              font.family: Style.font.family
              font.pixelSize: Math.min(21,keycap.height*.4,keycap.width/(text.length*.65))
              horizontalAlignment: Text.AlignHCenter
              verticalAlignment: Text.AlignVCenter
            }
            TapHandler {
              id: tap
              enabled: keyboard.enabled
              onTapped: keyboard.keyRequested(keycap.modelData.code)
            }
          }
        }
      }
    }
  }
}

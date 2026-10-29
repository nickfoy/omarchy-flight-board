import QtQuick
import Quickshell
import "../lock" as Lock

ShellRoot {
  readonly property bool portraitPreview: Quickshell.env("TOUCH_PREVIEW_PORTRAIT") === "1"
  FloatingWindow {
    id: window
    visible: true
    implicitWidth: portraitPreview ? 900 : 1440
    implicitHeight: portraitPreview ? 1440 : 900
    property int submitted: 0
    Lock.LockHost {
      id: host
      anchors.fill: parent
      designId: "split"
      loadBackground: false
      touchKeyboardAvailable: true
      touchKeyboardAutoShow: true
      onPasswordTextEdited: function(text) {passwordText=text}
      onClearFailureRequested: failureMessage=""
      onSubmitPassword: function(text) {
        if(text!=="dummyA!" && text!=="physical-fallback")throw new Error("Wrong synthetic submission")
        window.submitted++
      }
    }
    Timer {
      interval: 1000
      running: true
      onTriggered: {
        if(!host.ready)throw new Error("Lock design failed to load")
        if(Quickshell.env("TOUCH_PREVIEW_BROKEN") === "1") {
          if(host.touchKeyboardReady)throw new Error("Broken model unexpectedly loaded")
          host.passwordText="physical-fallback"
          host.handleTouchKey("a")
          if(host.passwordText!=="physical-fallback")throw new Error("Failed keyboard changed input")
          host.item.submitPassword(host.passwordText)
          if(window.submitted!==1)throw new Error("Existing design submission unavailable")
          console.log("Broken keyboard model preserves lock host and existing submit path")
          Qt.quit()
          return
        }
        if(!host.touchKeyboardReady)throw new Error("Touch keyboard did not load")
        host.passwordText="dummy"
        host.handleTouchKey("Shift");host.handleTouchKey("a")
        host.handleTouchKey("Shift");host.handleTouchKey("1")
        if(host.passwordText!=="dummyA!")throw new Error("Touch/physical composition failed")
        host.authenticatingPassword=true
        host.handleTouchKey("Unlock")
        if(window.submitted!==0)throw new Error("Busy input was submitted")
        host.authenticatingPassword=false
        host.handleTouchKey("Unlock")
        if(window.submitted!==1 || host.passwordText!=="")throw new Error("Submit did not clear input")
        host.handleTouchKey("Caps")
        host.inputEnabled=false
        if(host.touchCaps)throw new Error("Covered keyboard kept modifiers")
        host.handleTouchKey("a")
        if(host.passwordText!=="")throw new Error("Covered keyboard accepted input")
        host.inputEnabled=true
        host.touchKeyboardAwake=false
        host.handleTouchKey("a")
        if(host.passwordText!=="")throw new Error("Blanked keyboard accepted input")
        host.touchKeyboardAwake=true
        host.grabToImage(function(result){
          result.saveToFile(portraitPreview ? "/tmp/yoga-lock-keyboard-portrait.png" : "/tmp/yoga-lock-keyboard-landscape.png")
          console.log("Touch keyboard synthetic runtime checks passed")
          Qt.quit()
        })
      }
    }
  }
}

function entry(code, shifted, units) { return {code: code, shifted: shifted || "", units: units || 1}; }
function rows() {
  return [
    [entry("`","~"),entry("1","!"),entry("2","@"),entry("3","#"),entry("4","$"),entry("5","%"),entry("6","^"),entry("7","&"),entry("8","*"),entry("9","("),entry("0",")"),entry("-","_"),entry("=","+"),entry("Backspace","",1.8)],
    "qwertyuiop".split("").map(function(c){return entry(c)}).concat([entry("[","{"),entry("]","}"),entry("\\","|")]),
    "asdfghjkl".split("").map(function(c){return entry(c)}).concat([entry(";",":"),entry("'",'"')]),
    [entry("Shift","",1.8)].concat("zxcvbnm".split("").map(function(c){return entry(c)}),[entry(",","<"),entry(".",">"),entry("/","?"),entry("Shift","",1.8)]),
    [entry("Caps","",1.8),entry("Space","",6),entry("Clear","",1.8),entry("Unlock","",2.6)]
  ];
}
function label(k, shift, caps) {
  if (/^[a-z]$/.test(k.code)) return shift !== caps ? k.code.toUpperCase() : k.code;
  if (k.code === "Backspace") return "⌫";
  return shift && k.shifted ? k.shifted : k.code;
}
function applyKey(text, code, shift, caps) {
  var found = null;
  rows().forEach(function(row){row.forEach(function(k){if(k.code===code)found=k})});
  if (!found && code !== "Hide") return null;
  var result = {text:text,shift:!!shift,caps:!!caps,submit:false};
  if (code === "Shift") result.shift = !shift;
  else if (code === "Caps") result.caps = !caps;
  else if (code === "Clear") result.text = "";
  else if (code === "Backspace") {
    var count = text.length;
    var last = text.charCodeAt(count-1), before = text.charCodeAt(count-2);
    result.text = text.slice(0, Math.max(0,count-(last>=0xdc00 && last<=0xdfff && before>=0xd800 && before<=0xdbff ? 2 : 1)));
  } else if (code === "Unlock") result.submit = text.length > 0;
  else if (code !== "Hide") {
    result.text += code === "Space" ? " " : label(found,!!shift,!!caps);
    result.shift = false;
  }
  return result;
}

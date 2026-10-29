const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const model = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../lock/TouchKeyboardModel.js'), 'utf8'), model);
const key = (text, code, shift=false, caps=false) => model.applyKey(text, code, shift, caps);

test('letters, one-shot shift, caps and shifted punctuation match English keyboard', () => {
  assert.equal(key('', 'a').text, 'a');
  assert.equal(key('', 'a', true).text, 'A');
  assert.equal(key('', 'a', true).shift, false);
  assert.equal(key('', 'a', false, true).text, 'A');
  assert.equal(key('', 'a', true, true).text, 'a');
  assert.equal(key('', '1', true).text, '!');
  assert.equal(key('', '1', false, true).text, '1');
  assert.equal(key('', '\\', true).text, '|');
  assert.equal(key('', 'Space').text, ' ');
  assert.equal(key('', 'Shift').shift, true);
  assert.equal(key('', 'Caps').caps, true);
});
test('keyboard can enter every printable ASCII character', () => {
  const available = new Set([' ']);
  for (const row of model.rows()) for (const entry of row) {
    if (entry.code.length === 1) {
      available.add(key('', entry.code).text);
      available.add(key('', entry.code, true).text);
    }
  }
  for (let code=32;code<=126;code++) assert.ok(available.has(String.fromCharCode(code)), `missing character ${code}`);
});
test('editing clears and removes complete Unicode code points without submitting', () => {
  assert.equal(key('ab', 'Backspace').text, 'a');
  assert.equal(key('a😀', 'Backspace').text, 'a');
  assert.equal(key('', 'Backspace').text, '');
  assert.equal(key('ab', 'Clear').text, '');
  assert.equal(key('ab', 'Backspace').submit, false);
  assert.equal(key('ab', 'Unlock').submit, true);
  assert.equal(key('', 'Unlock').submit, false);
  assert.equal(key('ab', 'not-a-key'), null);
});

function hostFixture() {
  const emitted=[];
  const state={KeyboardModel:model, inputEnabled:true, authenticatingPassword:false,
    touchKeyboardAvailable:true, touchKeyboardOpen:true, touchShift:false, touchCaps:false,
    touchKeyboardAwake:true, touchKeyboard:{item:{applyKey:model.applyKey}},
    fido2Active:false, passwordText:'', failureMessage:'',
    wakeRequested() {}, forcePasswordFocus() {},
    passwordRequested() {if(state.fido2Active){state.fido2Active=false;state.passwordText='';}},
    clearFailureRequested() {state.failureMessage='';},
    passwordTextEdited(text) {state.passwordText=text;emitted.push(['edit',text]);},
    submitPassword(text) {emitted.push(['submit',text]);}
  };
  state.host=state;
  const source=fs.readFileSync(path.join(__dirname,'../lock/LockHost.qml'),'utf8');
  vm.createContext(state);
  for(const name of ['resetTouchKeyboard','handleTouchKey']) {
    const start=source.indexOf(`  function ${name}(`);
    assert.notEqual(start,-1,`missing ${name}`);
    const end=source.indexOf('\n  }',start);
    vm.runInContext(source.slice(start,end+4),state);
  }
  return {state,emitted};
}
test('touch edits join physical input and clear shared state before existing submit signal', () => {
  const {state:s,emitted}=hostFixture();
  s.passwordText='physical';s.handleTouchKey('1');s.handleTouchKey('Unlock');
  assert.deepEqual(emitted,[['edit','physical1'],['edit',''],['submit','physical1']]);
});
test('hidden, covered, unavailable or authenticating keyboards cannot edit or submit', () => {
  for(const blocked of [{inputEnabled:false},{authenticatingPassword:true},{touchKeyboardOpen:false},{touchKeyboardAvailable:false}]) {
    const {state:s,emitted}=hostFixture();Object.assign(s,blocked,{passwordText:'dummy'});
    s.handleTouchKey('a');s.handleTouchKey('Unlock');
    assert.deepEqual(emitted,[]);
    assert.equal(s.passwordText,'dummy');
  }
});
test('failure recovery, alternate auth and hide reset do not leak previous input', () => {
  const {state:s,emitted}=hostFixture();
  s.failureMessage='Failed';s.handleTouchKey('a');assert.equal(s.failureMessage,'');
  s.fido2Active=true;s.passwordText='old pin';s.handleTouchKey('b');
  assert.equal(s.passwordText,'b');assert.equal(s.fido2Active,false);
  s.touchShift=true;s.touchCaps=true;s.handleTouchKey('Hide');
  assert.equal(s.touchKeyboardOpen,false);assert.equal(s.touchShift,false);assert.equal(s.touchCaps,false);
  assert.equal(emitted.some(([kind])=>kind==='submit'),false);
});
test('unknown keys and empty unlock do not invoke authentication', () => {
  const {state:s,emitted}=hostFixture();s.handleTouchKey('unknown');s.handleTouchKey('Unlock');
  assert.deepEqual(emitted,[]);
});
test('missing keyboard component preserves the physical input and blanked taps only wake', () => {
  const {state:s,emitted}=hostFixture();s.passwordText='physical';
  s.touchKeyboard.item=null;s.handleTouchKey('a');s.handleTouchKey('Unlock');
  assert.equal(s.passwordText,'physical');assert.deepEqual(emitted,[]);
  s.touchKeyboard.item={applyKey:model.applyKey};s.touchKeyboardAwake=false;
  let wakes=0;s.wakeRequested=()=>wakes++;
  s.handleTouchKey('a');s.handleTouchKey('Unlock');
  assert.equal(s.passwordText,'physical');assert.deepEqual(emitted,[]);assert.equal(wakes,2);
});

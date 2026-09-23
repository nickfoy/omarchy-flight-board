const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {test} = require('node:test');
const source = fs.readFileSync(require('node:path').join(__dirname, '../lock/Service.qml'), 'utf8');
function fixture() {
  let now = 100000;
  const context = {
    Date: {now: () => now}, Math,
    lockRequested: true, boardCycleActive: false, boardCoverVisible: false,
    boardScreenOffAt: 0, boardBlankDelay: 0, lockedBoardScreenOffMs: 3600000,
    authenticatingPassword: false, screenBlanked: false, keepDisplayOn: false,
    enteredPassword: 'partial', pendingPassword: '', failureMessage: '',
    wakeProcess: {running: false}, blankProcess: {running: false},
    displayBlankingSuppressed: false,
    boardBlankTimer: {restarts: 0, restart() { this.restarts++; }},
    idleBlankTimer: {armedAt: 0, restarts: 0, stops: 0, restart() { this.restarts++; }, stop() {this.stops++;}},
    logEvent() {},
  };
  context.root = context;
  vm.createContext(context);
  for (const name of ['prepareBoardTimeout','handlePasswordIdle','handleBoardDeadline','runBlank','runWake','armBlankTimer','revealUnlockView']) {
    const start = source.indexOf(`  function ${name}(`);
    assert.notEqual(start, -1);
    const end = source.indexOf('\n  }', start);
    vm.runInContext(source.slice(start, end + 4), context);
  }
  return {state: context, advance: ms => now += ms};
}

test('idle password screen returns to board without unlocking or extending deadline', () => {
  const {state:s, advance} = fixture();
  s.prepareBoardTimeout(3180000);
  const deadline = s.boardScreenOffAt;
  advance(15000);
  s.handlePasswordIdle();
  assert.equal(s.boardCoverVisible, true);
  assert.equal(s.screenBlanked, false);
  assert.equal(s.lockRequested, true);
  assert.equal(s.boardScreenOffAt, deadline);
  assert.equal(s.enteredPassword, '');
});
test('activity reveals password and restarts full display idle deadline', () => {
  const {state:s, advance} = fixture();
  s.prepareBoardTimeout(20000);
  s.boardCoverVisible = true;
  advance(5000);
  s.revealUnlockView();
  assert.equal(s.boardCoverVisible, false);
  assert.equal(s.boardScreenOffAt, 105000 + 3600000);
  assert.equal(s.boardBlankTimer.restarts, 1);
  advance(15000);
  s.handlePasswordIdle();
  assert.equal(s.boardCoverVisible, true);
  assert.equal(s.boardScreenOffAt, 105000 + 3600000);
});
test('display deadline blanks cover while retaining session lock', () => {
  const {state:s, advance} = fixture();
  s.prepareBoardTimeout(20000);
  s.boardCoverVisible = true;
  advance(20000);
  s.handleBoardDeadline();
  assert.equal(s.boardCoverVisible, false);
  assert.equal(s.screenBlanked, true);
  assert.equal(s.lockRequested, true);
  s.handlePasswordIdle();
  assert.equal(s.boardCoverVisible, false);
});
test('password authentication is not interrupted by cover or display-off', () => {
  const {state:s} = fixture();
  s.prepareBoardTimeout(20000);
  s.authenticatingPassword = true;
  s.handlePasswordIdle();
  s.handleBoardDeadline();
  assert.equal(s.boardCoverVisible, false);
  assert.equal(s.screenBlanked, false);
  assert.equal(s.enteredPassword, 'partial');
  assert.equal(s.boardBlankTimer.restarts, 1);
});
test('without flight board integration original blanking still works', () => {
  const {state:s} = fixture();
  s.handlePasswordIdle();
  assert.equal(s.screenBlanked, true);
  assert.equal(s.boardCoverVisible, false);
});
test('waking after display-off returns to password then board on inactivity', () => {
  const {state:s, advance} = fixture();
  s.prepareBoardTimeout(20000);
  advance(20000);
  s.handleBoardDeadline();
  s.runWake();
  assert.equal(s.screenBlanked, false);
  assert.equal(s.boardCoverVisible, false);
  advance(15000);
  s.handlePasswordIdle();
  assert.equal(s.boardCoverVisible, true);
  assert.equal(s.lockRequested, true);
});

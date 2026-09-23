const {test} = require('node:test');
const assert = require('node:assert/strict');
const {timingError} = require('../static/timing.js');
const settings = values => Object.fromEntries(['screensaverMinutes','lockMinutes','screenOffMinutes'].map((k,i)=>[k,values[i]]));
test('accepts ordered timings including boundaries',()=>{
  for (const v of [[5,7,20],[1,2,3],[238,239,240]]) assert.equal(timingError(settings(v)), '');
});
test('rejects empty, fractional, boolean, and out-of-order timing',()=>{
  for (const v of [[0,7,20],[5,5,20],[8,7,20],[5,20,20],[5,7,241],[true,7,20],[5.5,7,20],['5',7,20]]) assert.notEqual(timingError(settings(v)), '');
});

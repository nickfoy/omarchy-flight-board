const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const registryPath = '/usr/share/omarchy/shell/services/PluginRegistry.qml';
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '../manifest.json')));

// Exercise the installed host's actual enable/restore functions, without a
// running shell, IPC, or any filesystem mutation. Missing host is a CI skip.
test('Omarchy enable/disable restores the stock locker and never disables idle', {skip: !fs.existsSync(registryPath)}, () => {
  const source = fs.readFileSync(registryPath, 'utf8');
  function method(name) {
    const start = source.indexOf(`  function ${name}(`);
    assert.notEqual(start, -1, `host still exposes ${name}`);
    const end = source.indexOf('\n  }', start);
    assert.notEqual(end, -1);
    return source.slice(start, end + 4);
  }
  let config = {plugins: [], disabledPlugins: ['omarchy.media'], idle: {lock: 420, screensaver: 421}};
  const context = {
    installedPlugins: {[manifest.id]: manifest},
    shellConfigMutator: fn => fn(config),
    pluginsChanged() {}, registryRevision: 0, lastEnableError: '', console,
    Util: {canonicalWidgetId: s => s, isPlainObject: v => v && typeof v === 'object' && !Array.isArray(v)},
    findEntryLocation: (cfg, id) => {
      const index = (cfg.plugins || []).findIndex(entry => entry.id === id);
      return index < 0 ? {found: false} : {found: true, kind: 'plugin', index};
    },
  };
  vm.createContext(context);
  for (const name of ['ensureConfigShape', 'isDisabled', 'removeDisabled', 'addDisabled', 'cloneShouldRestoreSource', 'setCloneShouldRestoreSource', 'restoreCloneSource', 'setEnabled']) {
    vm.runInContext(method(name), context);
  }
  assert.equal(manifest.omarchy.clonedFrom, 'omarchy.lock');
  assert.equal(context.setEnabled(manifest.id, true), true);
  assert.ok(config.disabledPlugins.includes('omarchy.lock'));
  assert.ok(!config.disabledPlugins.includes('omarchy.idle'));
  assert.ok(config.cloneSourceRestores.includes(manifest.id));
  assert.equal(context.setEnabled(manifest.id, false), true);
  assert.ok(!config.disabledPlugins.includes('omarchy.lock'));
  assert.ok(!config.disabledPlugins.includes('omarchy.idle'));
  assert.ok(!config.plugins.some(p => p.id === manifest.id));
  assert.ok(config.disabledPlugins.includes('omarchy.media'));
  assert.equal(config.idle.lock, 420);
});

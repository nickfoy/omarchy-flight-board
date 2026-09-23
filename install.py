#!/usr/bin/env python3
"""Review setup with `plan`; apply explicitly with `enable`; undo with `restore`."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'app'))
import integration
import server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'enable', 'restore'), default='plan', nargs='?')
    args = parser.parse_args()
    try:
        if args.action == 'plan':
            preferences = server.settings()
            result = {'plugin': integration.PLUGIN, 'installedPath': str(integration.CONFIG / 'omarchy/plugins' / integration.PLUGIN),
                      'screensaverMinutes': preferences['screensaverMinutes'], 'lockMinutes': preferences['lockMinutes'],
                      'screenOffMinutes': preferences['screenOffMinutes'],
                      'changes': ['Enable Flight Board as the lock replacement; keep stock idle enabled.',
                                  'Save fallback idle timing, with the stock terminal saver scheduled after locking.',
                                  'Record original idle timing for compare-and-restore removal.'],
                      'requires': 'Unlocked desktop, stock idle, stock or Flight Board locker, GTK 3, WebKit2 4.1, password PAM.',
                      'restore': 'Run install.py restore before omarchy plugin remove nickfoy.flight-board.'}
        else:
            result = integration.change(args.action)
        print(json.dumps(result, indent=2))
    except (ValueError, RuntimeError, OSError, __import__('subprocess').SubprocessError) as error:
        parser.exit(1, f'Flight Board: {error}\n')


if __name__ == '__main__':
    main()

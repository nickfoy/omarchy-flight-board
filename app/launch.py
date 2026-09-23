#!/usr/bin/env python3
"""GTK/WebKit native window; --screensaver opens a fullscreen board on each monitor."""
import argparse
import signal
import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, Gdk, GLib, GLibUnix, WebKit2
from server import make_server

parser = argparse.ArgumentParser()
parser.add_argument('--screensaver', action='store_true')
parser.add_argument('--settings', action='store_true')
parser.add_argument('--windowed', action='store_true')
parser.add_argument('--app-id', choices=['org.omarchy.screensaver'], help=argparse.SUPPRESS)
args = parser.parse_args()
GLib.set_prgname('org.omarchy.screensaver' if args.screensaver else 'org.omarchy.splitflap')
GLib.set_application_name('Flight Board')
httpd = make_server()
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f'Split-Flap Board: http://127.0.0.1:{httpd.server_port}', flush=True)
windows = []

def stop(*unused):
    Gtk.main_quit()
    return False

display = Gdk.Display.get_default()
if display is None:
    raise SystemExit('A graphical desktop session is required.')
for index in range(display.get_n_monitors() if args.screensaver else 1):
    window = Gtk.Window(title='Flight Board')
    window.set_default_size(1400, 900)
    window.set_icon_from_file(str(__import__('pathlib').Path(__file__).parent / 'static/icon.svg'))
    manager = WebKit2.UserContentManager()
    manager.register_script_message_handler('native')
    def message(manager, result, target=window):
        action = result.get_js_value().to_string()
        if action == 'dismiss':
            stop()
        elif action == 'lock-appearance' and not args.screensaver:
            subprocess.Popen(['omarchy-shell', 'shell', 'summon', 'nickfoy.flight-board', '{"page":"lock"}'])
        elif action == 'fullscreen':
            if target.get_window().get_state() & Gdk.WindowState.FULLSCREEN:
                target.unfullscreen()
            else:
                target.fullscreen()
        elif action == 'leave-fullscreen':
            target.unfullscreen()
    manager.connect('script-message-received::native', message)
    view = WebKit2.WebView.new_with_user_content_manager(manager)
    web_settings = view.get_settings()
    web_settings.set_enable_developer_extras(False)
    web_settings.set_enable_write_console_messages_to_stdout(True)
    view.set_background_color(Gdk.RGBA(.063, .071, .059, 1))
    def navigation(view, decision, kind):
        if kind == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            uri = decision.get_navigation_action().get_request().get_uri()
            if not uri.startswith(f'http://127.0.0.1:{httpd.server_port}/'):
                if uri == 'https://www.avinor.no' or uri == 'https://www.avinor.no/':
                    Gtk.show_uri_on_window(None, uri, Gdk.CURRENT_TIME)
                decision.ignore()
                return True
        return False
    view.connect('decide-policy', navigation)
    window.add(view)
    window.connect('destroy', stop)
    window.show_all()
    if args.screensaver:
        window.fullscreen_on_monitor(window.get_screen(), index)
    elif args.windowed:
        window.maximize()
    else:
        window.fullscreen()
    query = '?screensaver=1' if args.screensaver else '?settings=1' if args.settings else ''
    view.load_uri(f'http://127.0.0.1:{httpd.server_port}/{query}')
    windows.append(window)

GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
try:
    Gtk.main()
finally:
    httpd.shutdown()
    httpd.server_close()

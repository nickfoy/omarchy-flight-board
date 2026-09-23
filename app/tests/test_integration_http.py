import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import server


class SetupHttpTests(unittest.TestCase):
    def request(self, payload, origin='http://127.0.0.1:12345', cookie='board_session_12345=test'):
        body = json.dumps(payload).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.path = '/api/integration'
        handler.server = SimpleNamespace(server_port=12345, token='test')
        handler.headers = {'Origin': origin, 'Cookie': cookie, 'Content-Length': str(len(body)), 'Host': '127.0.0.1:12345'}
        handler.rfile = io.BytesIO(body)
        responses = []
        handler.send = lambda value, code=200: responses.append((code, value))
        handler.do_POST()
        return responses[0]

    def test_setup_requires_same_origin_and_session_cookie(self):
        with patch.object(server.integration, 'change') as change:
            self.assertEqual(self.request({'action': 'enable'}, origin='https://example.com')[0], 403)
            self.assertEqual(self.request({'action': 'enable'}, cookie='')[0], 403)
            change.assert_not_called()

    def test_explicit_setup_action_returns_verified_status(self):
        with patch.object(server.integration, 'change') as change, patch.object(server.integration, 'status', return_value={'active': True, 'configured': True}):
            code, result = self.request({'action': 'enable'})
            self.assertEqual(code, 200)
            self.assertTrue(result['active'])
            change.assert_called_once_with('enable')

    def test_arbitrary_actions_cannot_execute(self):
        with patch.object(server.integration, 'change') as change:
            self.assertEqual(self.request({'action': 'shell command'})[0], 400)
            self.assertEqual(self.request([])[0], 400)
            change.assert_not_called()

    def test_setup_failures_reach_the_settings_ui(self):
        with patch.object(server.integration, 'change', side_effect=RuntimeError('Kept newer user edits')):
            code, result = self.request({'action': 'restore'})
            self.assertEqual(code, 409)
            self.assertIn('Kept newer user edits', result['error'])

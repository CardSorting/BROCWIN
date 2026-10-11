"""A rejected late action must not send an earlier click from the batch."""
import unittest
from unittest.mock import MagicMock
import capture
from capture import apply_input, apply_breakpoint_request, PlaywrightError


class CaptureInput(unittest.TestCase):
    def test_control_read_retries_without_losing_the_request(self):
        request_file = MagicMock()
        request_file.read_text.side_effect = [
            PermissionError(13, 'Permission denied'), FileNotFoundError(),
            '{"id":', '{"id":40,"input":[{"type":"press","key":"KeyX"}]}']
        result = {}
        # This mirrors the interrupted replay's real call site on the old
        # version, so its control fails on PermissionError rather than an
        # absent function. Each poll must leave input dispatch to the caller.
        read = getattr(capture, 'read_control_request',
                       lambda p, r: capture.json.loads(p.read_text(encoding='utf-8')))
        for _ in range(3):
            self.assertIsNone(read(request_file, result))
        self.assertEqual(read(request_file, result)['id'], 40)
        self.assertEqual(result['controlReadRetries']['count'], 2)
        self.assertNotIn('captureError', result)

    def test_rejected_probe_does_not_abort_capture_or_prevent_next_request(self):
        page = MagicMock()
        page.evaluate.side_effect = [PlaywrightError('Invalid breakpoint memory read'), 0]
        result = {}
        bad = {'id': 12, 'breakpointScope': 'all', 'breakpoints': [
            {'address': 0x328fb1e0, 'memory': [
                {'register': 'ecx', 'offset': 0x1000a0, 'size': 24}]}]}
        rejection = apply_breakpoint_request(page, bad, result, 803)
        self.assertEqual(rejection['phase'], 'breakpoint-plan')
        self.assertIn('Invalid breakpoint memory read', rejection['requestError'])
        self.assertNotIn('captureError', result)
        self.assertNotIn('breakpointPlans', result)
        self.assertIsNone(apply_breakpoint_request(page,
            {'id': 13, 'breakpoints': [], 'breakpointScope': 'all'}, result, 804))
        self.assertEqual(result['breakpointPlans'][0]['id'], 13)
        self.assertEqual(len(result['rejectedRequests']), 1)

    def test_batch_validation_precedes_input(self):
        page = MagicMock()
        page.locator.return_value.evaluate.return_value = {'width': 1024, 'height': 768}
        for bad in ({'type': 'wait', 'milliseconds': 6000}, {'type': 'text', 'text': 12},
                    {'type': 'click', 'x': 1024, 'y': 0},
                    *({'type': 'click', 'x': 505, 'y': 191, 'holdMilliseconds': value}
                      for value in [-1, 5001, True, 1.5, '1000']), None):
            with self.assertRaises(ValueError):
                apply_input(page, [{'type': 'click', 'x': 505, 'y': 191}, bad])
            page.mouse.click.assert_not_called()
            page.keyboard.type.assert_not_called()

    def test_valid_wait_and_text_redaction(self):
        page = MagicMock()
        page.locator.return_value.evaluate.return_value = {'width': 1024, 'height': 768}
        events = apply_input(page, [{'type': 'wait', 'milliseconds': 5000},
                                    {'type': 'text', 'text': 'local-test'}])
        page.wait_for_timeout.assert_called_once_with(5000)
        self.assertNotIn('local-test', repr(events))
        self.assertTrue(events[1]['textRedacted'])


if __name__ == '__main__':
    unittest.main()

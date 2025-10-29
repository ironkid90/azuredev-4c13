import unittest
from unittest.mock import patch, MagicMock

from agents import cli


class TestCli(unittest.TestCase):
    @patch("agents.thread_templates.create_client")
    @patch("agents.thread_templates.init_thread")
    @patch("agents.thread_templates.run_agent_once")
    @patch("agents.thread_templates.collect_messages")
    def test_main_generator(self, mock_collect, mock_run, mock_init, mock_client):
        # Setup mocks
        mock_proj = MagicMock()
        mock_client.return_value = mock_proj

        mock_thread = MagicMock()
        mock_thread.id = "thread-123"
        mock_init.return_value = mock_thread

        mock_run.return_value = MagicMock(status="succeeded")
        mock_collect.return_value = [{"role": "assistant", "text": "ok"}]

        result = cli.main(["generator", "Do something"])
        self.assertEqual(result, 0)
        mock_client.assert_called()
        mock_init.assert_called_with(mock_proj, "generator", user_prompt="Do something")
        mock_run.assert_called()
        mock_collect.assert_called_with(mock_proj, "thread-123")


if __name__ == "__main__":
    unittest.main()

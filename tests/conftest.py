"""Test-wide fixtures.

Inject a dummy ANTHROPIC__API_KEY so `Settings()` validates in tests that
never hit the API. Tests that exercise AnthropicClient directly should still
mock the network or skip when no real key is configured.
"""

import os

os.environ.setdefault("ANTHROPIC__API_KEY", "test-dummy-key")

# Change import if you have changed name of service.py
from daeploy.testing import patch
import service

# Test functions should always start with test_...
# Daeploy tests use the pytest package

# Example tests:


def test_hello():
    # Test that service.hello("Bob") returns what is expected
    assert service.hello("Bob") == "Hello Bob"


# Add your tests here

"""
This is a sample test file
"""
import pytest
import python_template  # noqa


class TestNothing:
    @pytest.mark.xfail
    def test_nothing(self):
        assert False

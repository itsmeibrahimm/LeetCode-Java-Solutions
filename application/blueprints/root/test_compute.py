# standard library imports
import pytest

# local application imports
from .compute import compute_random_inclusive


@pytest.mark.parametrize("low,high", [(1, 2), (-100, -1), (-1, +1), (0, 0)])
def test_compute_random_inclusive(low, high):
    assert low <= compute_random_inclusive(low, high) <= high

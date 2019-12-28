import os
import sys
import pytest

from realestate_com_au import RealestateComAu


def test_constructor():
    api = RealestateComAu()
    assert api

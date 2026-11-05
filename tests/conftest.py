"""Pytest fixtures and configuration for CoreSync test suite."""

import os
import sys

# Crucial: Override display plugins before any Qt imports occur in tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_PLATFORMTHEME"] = ""
os.environ["MPLCONFIGDIR"] = "/tmp/coresync_test_mpl"

from pathlib import Path
import pytest
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped PySide6 QApplication fixture."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_numeric_array():
    """Provide a reproducible 1D numpy array."""
    return np.arange(10_000, dtype=np.float64)


@pytest.fixture
def sample_matrix():
    """Provide a reproducible 2D square numpy matrix."""
    return np.random.RandomState(42).randn(100, 100)

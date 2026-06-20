import pytest

from fiscal_model import loaders


@pytest.fixture(scope="session")
def data():
    """Load & validate all files once for the whole test session (load is ~4s)."""
    return loaders.load_all(validate=True)

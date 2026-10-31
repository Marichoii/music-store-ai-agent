import pytest

from music_store.catalog import Catalog
from music_store.policies import PolicyBook
from music_store.tools import StoreTools


@pytest.fixture(scope="module")
def store_tools():
    return StoreTools(Catalog.load(), PolicyBook())

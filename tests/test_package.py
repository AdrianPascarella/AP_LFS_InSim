from importlib.metadata import version
from importlib.resources import files

import lfs_insim


def test_version_matches_installed_metadata() -> None:
    assert lfs_insim.__version__ == version("lfs-insim")


def test_package_declares_inline_types() -> None:
    assert files(lfs_insim).joinpath("py.typed").is_file()

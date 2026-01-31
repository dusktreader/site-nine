import tomllib
from importlib import metadata


def get_version_from_metadata() -> str:
    # Package is installed as "site-nine" and imported as "s9"
    return metadata.version("site-nine")


def get_version_from_pyproject() -> str:
    with open("pyproject.toml", "rb") as file:
        return tomllib.load(file)["project"]["version"]


def get_version() -> str:
    try:
        return get_version_from_metadata()
    except metadata.PackageNotFoundError:
        try:
            return get_version_from_pyproject()
        except (FileNotFoundError, KeyError):
            return "unknown"


__version__ = get_version()

import setuptools
import ast
import re
from pathlib import Path

CURRENT_DIR = Path(__file__).parent


def get_long_description() -> str:
    readme_md = CURRENT_DIR / "README.md"
    with open(readme_md, encoding="utf8") as ld_file:
        return ld_file.read()


def get_version() -> str:
    black_py = CURRENT_DIR / "realestate_com_au/__init__.py"
    _version_re = re.compile(r"__version__\s+=\s+(?P<version>.*)")
    with open(black_py, "r", encoding="utf8") as f:
        match = _version_re.search(f.read())
        version = match.group("version") if match is not None else '"unknown"'
    return str(ast.literal_eval(version))


setuptools.setup(
    name="realestate_com_au_api",
    version=get_version(),
    author="Tom Quirk",
    author_email="tomquirkacc@gmail.com",
    description="Python wrapper for the realestate.com.au API",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/tomquirk/realestate-com-au-api",
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=["requests", "fajita"],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)

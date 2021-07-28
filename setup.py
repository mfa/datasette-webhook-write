from setuptools import setup
import os

VERSION = "0.1"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="datasette-webhook-write",
    description="Datasette plugin to write to database via verified webhooks",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Andreas Madsack",
    url="https://github.com/mfa/datasette-webhook-write",
    project_urls={
        "Issues": "https://github.com/mfa/datasette-webhook-write/issues",
        "CI": "https://github.com/mfa/datasette-webhook-write/actions",
        "Changelog": "https://github.com/mfa/datasette-webhook-write/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["datasette_webhook_write"],
    entry_points={"datasette": ["webhook_write = datasette_webhook_write"]},
    install_requires=["datasette"],
    extras_require={"test": ["httpx", "pytest", "pytest-asyncio"]},
    tests_require=["datasette-webhook-write[test]"],
    python_requires=">=3.6",
)

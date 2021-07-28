# datasette-webhook-write

[![PyPI](https://img.shields.io/pypi/v/datasette-webhook-write.svg)](https://pypi.org/project/datasette-webhook-write/)
[![Changelog](https://img.shields.io/github/v/release/mfa/datasette-webhook-write?include_prereleases&label=changelog)](https://github.com/mfa/datasette-webhook-write/releases)
[![Tests](https://github.com/mfa/datasette-webhook-write/workflows/Test/badge.svg)](https://github.com/mfa/datasette-webhook-write/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mfa/datasette-webhook-write/blob/main/LICENSE)

Datasette plugin to write to databae via verified webhooks

## Installation

Install this plugin in the same environment as Datasette.

    $ datasette install datasette-webhook-write

## Usage

This plugin allows writing to a datasette database via hmac-signed http POST calls.

Example for metadata.yml (for usage to receive texts from https://nlg.ax/):
```
plugins:
  datasette-webhook-write:
    webhook_secret:
      "$env": "WEBHOOK_SECRET"
    http_header_name: "x-myax-signature"
    database_name: "example"
    table_name: "generated_texts"
    use_pk:
      - "uid"
      - "collection_id"
```

WEBHOOK_SECRET is set as environment variable.


## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-webhook-write
    python3 -mvenv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest

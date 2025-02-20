# datasette-webhook-write

[![PyPI](https://img.shields.io/pypi/v/datasette-webhook-write.svg)](https://pypi.org/project/datasette-webhook-write/)
[![Changelog](https://img.shields.io/github/v/release/mfa/datasette-webhook-write?include_prereleases&label=changelog)](https://github.com/mfa/datasette-webhook-write/releases)
[![Tests](https://github.com/mfa/datasette-webhook-write/workflows/Test/badge.svg)](https://github.com/mfa/datasette-webhook-write/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mfa/datasette-webhook-write/blob/main/LICENSE)

Datasette plugin to write to database via verified webhooks

## Installation

Install this plugin in the same environment as Datasette.

    $ datasette install datasette-webhook-write


## Usage (datasette/receiving side)

This plugin allows writing to a datasette database via hmac-signed http POST calls.

Example for metadata.yml (for usage to receive texts from https://nlg.ax/):

```yaml
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

`WEBHOOK_SECRET` is set as environment variable.

The url to upload to the datasette instance is ``/-/webhook-write/``.


## Usage (pushing side)

The json data pushed has to be signed with the `WEBHOOK_SECRET` and added to the headers of the POST call.

Generate the hmac signature (where `document` is the data you want to send, and `WEBHOOK_SECRET` is the secret only pushing+receving parties should know):

```python
digest = hmac.new(
    key=WEBHOOK_SECRET.encode(),
    msg=json.dumps(document).encode(),
    digestmod=hashlib.sha1,
)

header = {
    "X-SIGNATURE": f"sha1={digest.hexdigest()}",
}
```

The pushed data is written to the database only when secret+document are generating the same digest.


## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-webhook-write
    python -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    python -m pip install -e '.[test]'

To run the tests:

    python -m pytest

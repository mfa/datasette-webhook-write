import datetime
import hashlib
import hmac
import json

import sqlite_utils
from datasette import hookimpl
from datasette.utils import sqlite3
from datasette.utils.asgi import Response

__version__ = "0.5"


def check_signature(sig, data, secret, digestmod):
    try:
        signature_header = sig.replace("sha1=", "")
        signature_content = hmac.new(
            key=secret.encode("utf-8"), msg=data, digestmod=getattr(hashlib, digestmod)
        ).hexdigest()
    except AttributeError:
        pass
    except KeyError:
        pass
    except Exception:
        raise
    else:
        return bool(signature_header == signature_content)
    return False


def return_error(message):
    print(message, flush=True)
    return Response.json({"error": message, "status": 500}, status=500)


async def insert_webhook_data(request, datasette):
    if request.method != "POST":
        return Response.json(
            {"error": "only POST is allowed", "status": 400}, status=400
        )

    plugin_config = datasette.plugin_config("datasette-webhook-write") or {}

    secret = plugin_config.get("webhook_secret", "")
    if not secret:
        return return_error(">webhook_secret< needs to be configured in metadata.")

    http_header_name = plugin_config.get("http_header_name", "")
    if not http_header_name:
        return return_error(">http_header_name< needs to be configured in metadata.")

    table_name = plugin_config.get("table_name", "")
    if not table_name:
        return return_error(">table_name< needs to be configured in metadata.")

    database_name = plugin_config.get("database_name", "")
    if not database_name:
        return return_error(">database_name< needs to be configured in metadata.")
    db = datasette.get_database(database_name)
    if not db:
        return return_error(">database_name< needs to be a valid database.")

    # if not set, there will be no replacement of already existing datasets
    use_pk = plugin_config.get("use_pk")
    if isinstance(use_pk, list):
        use_pk = tuple(use_pk)

    data = await request.post_body()

    try:
        post_json = json.loads(data)
    except json.decoder.JSONDecodeError:
        return Response.json({"error": "wrong format", "status": 400}, status=400)

    digestmod = plugin_config.get("digestmod", "sha1")
    signature = request.headers.get(http_header_name)
    if not check_signature(signature, data, secret, digestmod):
        return Response.json({"error": "Permission denied", "status": 403}, status=403)

    if "text_modified" not in post_json:
        post_json["text_modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def insert(conn):
        db = sqlite_utils.Database(conn)
        if use_pk:
            db[table_name].insert_all(
                [post_json],
                replace=True,
                pk=use_pk,
            )
        else:
            db[table_name].insert_all([post_json])
        return

    try:
        await db.execute_write_fn(insert, block=True)
    except sqlite3.OperationalError as ex:
        if "has no column" in str(ex):
            return Response.json(
                {"status": 400, "error": str(ex), "error_code": "unknown_keys"},
                status=400,
            )
        else:
            return Response.json({"error": str(ex), "status": 500}, status=500)

    return Response.json("OK")


@hookimpl
def register_routes():
    return [
        (r"^/-/webhook-write/$", insert_webhook_data),
    ]

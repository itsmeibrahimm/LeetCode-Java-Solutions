import base64
import json
import typing


def encode_stream_cursor(cursor: typing.Optional[dict]) -> typing.Optional[str]:
    if not cursor or not isinstance(cursor, dict):
        return None

    cursor_json = json.dumps(cursor)
    cursor_enc = base64.b64encode(cursor_json.encode())
    return cursor_enc.decode("utf-8").strip()


def decode_stream_cursor(cursor: str = None) -> dict:
    if not cursor or not isinstance(cursor, str) or len(cursor) <= 0:
        return {}

    try:
        cursor_bytes = cursor.encode("utf-8")
        cursor_decoded = base64.b64decode(cursor_bytes)
        cursor_json = cursor_decoded.decode("utf-8")
        cursor_dict = json.loads(cursor_json)
        assert isinstance(cursor_dict, dict)
        return cursor_dict
    except Exception:
        return {}

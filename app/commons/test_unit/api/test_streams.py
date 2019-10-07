import pytest

from app.commons.api.streams import decode_stream_cursor, encode_stream_cursor

pytestmark = pytest.mark.asyncio


async def test_encode_with_empty_input():
    actual = encode_stream_cursor(None)
    assert actual is None, "encoding an empty input returns None"


async def test_encode_with_complex_input_returns_string():
    actual = encode_stream_cursor({"foo": "bar", "count": 3, "yes?": False})
    assert (
        actual == "eyJmb28iOiAiYmFyIiwgImNvdW50IjogMywgInllcz8iOiBmYWxzZX0="
    ), "encoding a complex input returns encoded string"


async def test_decode_with_invalid_input():
    actual = decode_stream_cursor("invalid")
    assert actual == {}, "decoding invalid input returns empty dictionary"


async def test_decode_with_complex_input():
    actual = decode_stream_cursor(
        "eyJmb28iOiAiYmFyIiwgImNvdW50IjogMywgInllcz8iOiBmYWxzZX0="
    )
    assert actual == {
        "foo": "bar",
        "count": 3,
        "yes?": False,
    }, "decoding complex input returns expected results"

import asyncio
import pytest

from app.commons.database.client.error_handlers import translate_db_error


class TestHandleDBError:
    def test_should_raise_exception_when_used_on_async_function(self):
        @translate_db_error
        def foo():
            return "foo"

        with pytest.raises(Exception) as e:
            foo()
            assert (
                e.message
                == "translate_db_error decorator can only be used in async functions."
            )

    def test_should_not_raise_exception_when_used_on_sync_function(self):
        @translate_db_error
        async def bar():
            return "bar"

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(bar())
        assert result == "bar"

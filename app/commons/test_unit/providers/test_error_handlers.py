import pytest

from app.commons.providers.stripe.error_handlers import handle_stripe_error


class TestHandleStripeError:
    def test_should_raise_exception_when_used_on_async_function(self):
        @handle_stripe_error
        async def foo():
            return "foo"

        with pytest.raises(Exception) as e:
            foo()
            assert (
                e.message
                == "handle_stripe_error decorator can't not used in async function."
            )

    def test_should_not_raise_exception_when_used_on_sync_function(self):
        @handle_stripe_error
        def bar():
            return "bar"

        assert bar() == "bar"

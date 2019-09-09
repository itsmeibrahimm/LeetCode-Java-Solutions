from app.commons.runtime import runtime


def test_runtime_setter(runtime_setter):
    file_name = "KYLE_LIKES_COLD_SANDWICHES.str"
    response = runtime.get_str(file_name, None)
    assert response is None

    runtime_setter.set(file_name, "yes")

    response = runtime.get_str(file_name, None)
    assert response == "yes"

    runtime_setter.remove(file_name)

    response = runtime.get_str(file_name, None)
    assert response is None

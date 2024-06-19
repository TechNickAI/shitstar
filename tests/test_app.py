from streamlit.testing.v1 import AppTest


def test_streamlit_app_runs():
    # Initialize the app
    at = AppTest.from_file("app.py")

    # Run the app
    at.run(timeout=10_000)

    # Check if the app ran without exceptions
    assert not at.exception, "Streamlit app encountered an exception"

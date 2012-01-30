import logbook


null_handler = logbook.NullHandler()

def setup_package():
    null_handler.push_application()

def teardown_package():
    null_handler.pop_application()

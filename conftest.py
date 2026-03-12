def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests requiring a live Chrome browser and network access",
    )

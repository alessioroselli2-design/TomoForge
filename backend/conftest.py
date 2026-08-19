import os


# These suites exercise a running, paid external environment. They remain
# available to CI or a configured workspace, but must not be collected by the
# local configuration-only test run.
if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    collect_ignore = [
        "tests/backend_test.py",
        "tests/test_premium_admin.py",
        "tests/test_public_endpoints.py",
    ]
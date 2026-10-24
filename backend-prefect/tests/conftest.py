import os
import pytest
from cryptography.fernet import Fernet
from prefect.testing.utilities import prefect_test_harness
from app.api import create_app
from app.errors import AuthError
from app.settings import Settings


@pytest.fixture(scope="session", autouse=True)
def prefect_server():
    os.environ["PREFECT_SERVER_ANALYTICS_ENABLED"] = "false"
    with prefect_test_harness():
        yield


class FakeIdentity:
    def authenticate(self, email, password):
        if email != "student@example.test" or password != "correct-password":
            raise AuthError("Credenciales inválidas")
        return "student-1"


@pytest.fixture
def app(tmp_path):
    settings = Settings("j" * 48, Fernet.generate_key().decode(), "https://example.supabase.co",
                        "test-publishable", str(tmp_path / "mfa.db"))
    application = create_app(settings, FakeIdentity())
    yield application
    application.state.service.store.db.close()

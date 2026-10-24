import base64
import io
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import qrcode
from .errors import AuthError
from .flows import dispatch, login_flow, enrollment_flow, confirm_flow, verify_flow
from .provider import SupabaseIdentity
from .service import AuthService
from .settings import Settings


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256, repr=False)


class Code(BaseModel):
    code: str = Field(min_length=6, max_length=32, repr=False)
    strategy: Literal["totp", "backup"] = "totp"


def create_app(settings=None, identity=None):
    settings = settings or Settings.from_env()
    service = AuthService(settings, identity or SupabaseIdentity(settings))
    app = FastAPI(title="Laboratorio 2FA con Prefect", version="1.0.0")
    app.state.service = service
    bearer = HTTPBearer()

    @app.exception_handler(AuthError)
    async def auth_error(request, error):
        return JSONResponse(status_code=error.status,
                            content={"detail": str(error), "error": type(error).__name__})

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok", "identity_provider": "supabase"}

    @app.post("/auth/login")
    def login(body: Credentials):
        return dispatch(login_flow, service, **body.model_dump())

    @app.post("/auth/enroll/start")
    def enroll(body: Credentials):
        result = dispatch(enrollment_flow, service, **body.model_dump())
        buffer = io.BytesIO()
        qrcode.make(result["otpauth_uri"]).save(buffer, format="PNG")
        result["qr_data_url"] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        return result

    @app.post("/auth/enroll/confirm")
    def confirm(body: Code, credentials: HTTPAuthorizationCredentials = Depends(bearer)):
        return dispatch(confirm_flow, service, token=credentials.credentials, code=body.code)

    @app.post("/auth/verify-2fa")
    def verify(body: Code, credentials: HTTPAuthorizationCredentials = Depends(bearer)):
        return dispatch(verify_flow, service, token=credentials.credentials, **body.model_dump())

    @app.get("/api/boveda-secreta")
    def vault(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
        claims = service.claims(credentials.credentials, "access")
        return {"message": "Bienvenido a la bóveda secreta", "user_id": claims["sub"], "mfa_verified": True}

    web = Path(__file__).resolve().parents[2] / "web-login"
    app.mount("/static", StaticFiles(directory=web), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(web / "index.html")

    return app

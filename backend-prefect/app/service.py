import base64
from dataclasses import dataclass, field
import secrets
import threading
import time
from urllib.parse import quote, urlencode
import jwt
from .errors import AuthError
from .store import Store
from .strategies import TOTPStrategy, BackupCodeStrategy
from .totp import match_window


@dataclass(repr=False)
class RequestContext:
    service: object
    values: dict = field(repr=False)
    user_id: str = ""
    now: float = 0
    window: int | None = None
    output: dict = field(default_factory=dict, repr=False)


class AuthService:
    def __init__(self, settings, identity, clock=time.time):
        self.settings = settings
        self.identity = identity
        self.clock = clock
        self.store = Store(settings.database, settings.encryption_key, settings.jwt_secret)
        self.gate = threading.Lock()
        self.strategies = {"totp": TOTPStrategy(), "backup": BackupCodeStrategy()}

    def token(self, user_id, purpose):
        now = int(self.clock())
        ttl = 900 if purpose == "access" else 300
        return jwt.encode({"sub": user_id, "iss": "2fa-lab", "aud": "2fa-lab-api",
                           "iat": now, "exp": now + ttl, "jti": secrets.token_urlsafe(16),
                           "purpose": purpose, "mfa_verified": purpose == "access"},
                          self.settings.jwt_secret, algorithm="HS256")

    def claims(self, token, purpose):
        try:
            claims = jwt.decode(token, self.settings.jwt_secret, algorithms=["HS256"],
                                audience="2fa-lab-api", issuer="2fa-lab",
                                options={"require": ["sub", "exp", "iat", "jti", "purpose", "mfa_verified"]})
            if claims["purpose"] != purpose or claims["mfa_verified"] is not (purpose == "access"):
                raise AuthError("Este token no autoriza esta operación")
            return claims
        except jwt.InvalidTokenError:
            raise AuthError("Token inválido o expirado") from None

    def authenticate(self, context):
        email = context.values["email"].strip().lower()
        self.store.rate_limit("login:" + self.store.digest(email), self.clock(), maximum=20)
        context.user_id = self.identity.authenticate(email, context.values["password"])

    def login(self, context):
        factor = self.store.factor(context.user_id)
        context.output = {"pre_auth_token": self.token(context.user_id, "pre_auth"),
                          "expires_in": 300, "mfa_state": factor["state"] if factor else "NOT_ENROLLED"}

    def begin_enrollment(self, context):
        secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
        self.store.pending(context.user_id, secret, self.clock())
        label = "Laboratorio2FA:" + context.values["email"].strip().lower()
        uri = "otpauth://totp/" + quote(label, safe="") + "?" + urlencode({
            "secret": secret, "issuer": "Laboratorio2FA", "algorithm": "SHA1", "digits": 6, "period": 30})
        context.output = {"state": "PENDING_VERIFICATION", "secret": secret, "otpauth_uri": uri,
                          "enrollment_token": self.token(context.user_id, "enrollment")}

    def confirm_enrollment(self, context):
        context.user_id = self.claims(context.values["token"], "enrollment")["sub"]
        now = self.clock()
        self.store.rate_limit("mfa:" + context.user_id, now)
        factor = self.store.factor(context.user_id)
        if not factor or factor["state"] != "PENDING_VERIFICATION" or now - factor["created"] > 300:
            raise AuthError("Aprovisionamiento inexistente, activo o expirado")
        if match_window(factor["secret"], context.values["code"], now) is None:
            raise AuthError("Código de activación inválido")
        codes = [secrets.token_hex(8).upper() for _ in range(8)]
        self.store.commit_code(context.user_id, context.values["code"], now, activate_codes=codes)
        context.output = {"state": "ACTIVE", "backup_codes": codes,
                          "message": "Guarda estos códigos: se muestran una sola vez. Espera al siguiente TOTP para iniciar sesión."}

    def validate_pre_auth(self, context):
        context.user_id = self.claims(context.values["token"], "pre_auth")["sub"]
        context.now = self.clock()
        self.store.rate_limit("mfa:" + context.user_id, context.now)

    def execute_strategy(self, context):
        strategy = self.strategies.get(context.values["strategy"])
        if strategy is None:
            raise AuthError("Estrategia inválida")
        context.window = strategy.validate(self.store, context.user_id, context.values["code"], context.now)

    def issue(self, context):
        access = self.token(context.user_id, "access")
        self.store.commit_code(context.user_id, context.values["code"], context.now,
                               backup=context.values["strategy"] == "backup")
        context.output = {"access_token": access, "token_type": "bearer", "expires_in": 900,
                          "mfa_verified": True, "matched_window": context.window}

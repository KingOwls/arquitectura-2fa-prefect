from dataclasses import dataclass
import os
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    encryption_key: str
    supabase_url: str
    supabase_key: str
    database: str = "data/mfa.db"

    @classmethod
    def from_env(cls):
        load_dotenv()
        values = {key: os.getenv(key, "") for key in (
            "JWT_SECRET", "MFA_ENCRYPTION_KEY", "SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY"
        )}
        if not all(values.values()) or len(values["JWT_SECRET"]) < 32:
            raise RuntimeError("Configura .env siguiendo README; JWT_SECRET debe tener al menos 32 caracteres")
        if not values["SUPABASE_URL"].startswith("https://"):
            raise RuntimeError("SUPABASE_URL debe usar HTTPS")
        return cls(values["JWT_SECRET"], values["MFA_ENCRYPTION_KEY"],
                   values["SUPABASE_URL"].rstrip("/"), values["SUPABASE_PUBLISHABLE_KEY"],
                   os.getenv("MFA_DATABASE", "data/mfa.db"))

"""Supabase conserva las credenciales; sus sesiones nunca llegan al cliente web."""
import httpx
from .errors import AuthError, ProviderUnavailable


class SupabaseIdentity:
    def __init__(self, settings):
        self.url = settings.supabase_url
        self.key = settings.supabase_key

    def authenticate(self, email: str, password: str) -> str:
        try:
            response = httpx.post(
                f"{self.url}/auth/v1/token?grant_type=password",
                headers={"apikey": self.key},
                json={"email": email, "password": password}, timeout=15,
            )
        except httpx.RequestError:
            raise ProviderUnavailable("No fue posible contactar Supabase") from None
        if response.status_code >= 500:
            raise ProviderUnavailable("Supabase no está disponible")
        if response.status_code != 200:
            raise AuthError("Credenciales inválidas o correo sin confirmar")
        user_id = response.json().get("user", {}).get("id")
        if not user_id:
            raise ProviderUnavailable("Respuesta inválida de Supabase")
        return user_id

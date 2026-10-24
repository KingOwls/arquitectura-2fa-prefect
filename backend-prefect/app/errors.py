class AuthError(Exception):
    status = 401


class ReplayAttackDetected(AuthError):
    status = 409


class TooManyAttempts(AuthError):
    status = 429


class ProviderUnavailable(AuthError):
    status = 503

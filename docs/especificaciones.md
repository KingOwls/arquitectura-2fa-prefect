# Especificaciones del laboratorio

Base: guía entregada para Patrones Arquitectónicos Avanzados, “Implementación de Arquitectura 2FA (TOTP) desde Cero y Observabilidad con Prefect”. El documento original no se redistribuye en el repositorio público.

Decisiones acordadas: proyecto desde cero; desarrollo en Linux con React Native/Expo; usuarios en un Supabase existente; repositorio público `KingOwls/arquitectura-2fa-prefect`; apartado para video de sustentación.

| Requisito | Implementación | Evidencia |
| --- | --- | --- |
| TOTP de seis dígitos cada 30 s sin librería TOTP | `mobile-authenticator/totp.mjs` y `backend-prefect/app/totp.py` | Vectores RFC y demo de paridad |
| Ingreso QR o semilla manual | Base32/URI en móvil, QR generado por backend | Demo de aprovisionamiento |
| App sin conexión con contador | Timer basado en Unix time y actualización al volver al primer plano | Modo avión en Android |
| Usuarios Supabase y login web | Supabase Auth mediante backend; `web-login/` | Login con cuenta confirmada |
| Máquina de estados | Ausente → PENDING_VERIFICATION → ACTIVE | Tests de activación y rechazo de reemplazo |
| Step-Up | Tokens con `purpose` y `mfa_verified` verificados en servidor | Denegación de bóveda con pre-auth |
| Strategy | `SecondFactorStrategy`, `TOTPStrategy`, `BackupCodeStrategy` | Ambas estrategias probadas |
| Tolerancia C−1, C, C+1 | Ventanas de 30 s, log de ventana coincidente | Pruebas y log Prefect |
| Anti-replay 90 s | Hash de código y usuario en SQLite, serialización en proceso | HTTP 409 y tarea Failed |
| Observabilidad | Flows de login, aprovisionamiento y verificación; cuatro tareas exigidas | Dashboard Prefect |
| Entrega reproducible | Dos carpetas exigidas, web, README, lockfiles, CI | Clonar, instalar, probar |
| Sustentación | Sección de video y guion | Añadir grabación real |

Rúbrica: criptografía móvil 30%; patrones 30%; prevención de repetición 15%; Prefect 25%. Las pruebas automatizadas aportan evidencia técnica, pero no equivalen a una calificación ni sustituyen la demostración móvil.

La guía menciona Supabase y admite almacenamiento local para el laboratorio. Se resuelve usando Supabase Auth como base de usuarios y SQLite para estado MFA local cifrado. No se crea una tabla de contraseñas propia ni se modifica el esquema público existente.

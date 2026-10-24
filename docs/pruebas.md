# Pruebas y evidencias

## Automatizadas

- Python y JavaScript: vectores oficiales SHA1 de RFC 6238 y RFC 4226, incluidos ceros iniciales y límites de ventana.
- API con Supabase simulado: PENDING → ACTIVE, cifrado de semilla, separación de propósitos JWT, vencimiento y firma inválida.
- TOTP y respaldos: acceso elevado, eliminación definitiva del respaldo, rechazo de repetición y límite de intentos.
- Concurrencia y persistencia: una aceptación y un rechazo para dos envíos simultáneos; replay conservado tras reabrir SQLite.
- Prefect real temporal: tarea anti-replay y flow fallan; los parámetros de flows solo contienen el identificador opaco.
- Expo: exportación del bundle Android y de la vista web. No equivale a instalar un APK en un dispositivo.

## Aceptación manual obligatoria

| Ensayo | Procedimiento | Resultado esperado | Evidencia |
| --- | --- | --- | --- |
| Paridad | Misma semilla en app propia y Google/Microsoft Authenticator | Seis dígitos iguales simultáneamente | Pendiente de grabación |
| Modo avión | Abrir app móvil, desconectar, esperar cambio, escribir código en web del PC | Bóveda responde 200 | Pendiente de dispositivo |
| Replay | Pulsar Repetir último código antes de 30 s | 409 y check_anti_replay_cache Failed | Automatizado y pendiente de video |
| Respaldo/desfase | Seleccionar respaldo y usar uno guardado, o validar C−1/C+1 | Acceso y log de estrategia/ventana | Automatizado y pendiente de video |

Antes de grabar, reinicia el ensayo con un usuario de laboratorio y revisa el límite de cinco intentos MFA cada cinco minutos. La activación también cuenta como intento. No grabes contraseñas, semillas ni códigos de respaldo reutilizables. Puedes preparar el QR antes de grabar y mostrar solamente los códigos de seis dígitos.

## Diagnóstico

- Error de correo sin confirmar: verifica la cuenta en Supabase Authentication.
- HTTP 503: revisa conectividad y que Supabase esté activo.
- HTTP 401 con TOTP: sincroniza la hora del equipo y teléfono; comprueba la semilla y estado activo.
- HTTP 409 tras activar: espera al siguiente TOTP; el de activación ya está consumido.
- HTTP 429: espera cinco minutos desde el inicio de la ventana de intentos.
- Sin flujos en el dashboard: revisa `PREFECT_API_URL=http://127.0.0.1:4200/api` y que el servidor esté iniciado antes del backend.
- Modo avión en Expo Go: carga antes el bundle y mantén la app abierta. Para arranque completamente independiente usa una compilación Android de distribución local.

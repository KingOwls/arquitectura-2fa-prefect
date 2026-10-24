# Video de solución y sustentación

Estado: **pendiente de grabación**. Este apartado está preparado para adjuntar evidencia real de funcionamiento.

| Dato | Completar al publicar |
| --- | --- |
| Enlace del video | Pendiente |
| Integrantes | Pendiente |
| Fecha | Pendiente |
| Duración | Objetivo: 5 minutos |
| Commit demostrado | Copiar salida de `git rev-parse --short HEAD` |

## Preparación

Abre web, Prefect y Android. Usa una cuenta de laboratorio con 2FA activo y la misma semilla configurada en la app propia y en un Authenticator oficial. Guarda los respaldos sin mostrarlos en pantalla. Mantén el PC conectado; el teléfono es el dispositivo que pasará a modo avión. En Linux puedes grabar pantalla y micrófono con OBS o la herramienta de tu escritorio; muestra el teléfono mediante cámara o captura del emulador.

## Guion de cinco minutos

| Tiempo | Pantalla y acción | Explicación |
| --- | --- | --- |
| 0:00–0:35 | Repositorio y diagrama | “Supabase valida la identidad. Nuestro backend exige otro factor antes de abrir la bóveda.” |
| 0:35–1:15 | App propia y oficial con mismo código | “Calculamos HMAC-SHA1 con contador de 30 segundos y truncamiento dinámico, sin librería TOTP.” |
| 1:15–2:05 | Android en modo avión, esperar cambio de código | “La semilla y el reloj bastan; la aplicación no consulta un servidor para generar el código.” |
| 2:05–2:45 | Login web, intento con token temporal y luego TOTP | “La contraseña entrega pre-auth. Solo el segundo factor produce mfa_verified y acceso a la bóveda.” |
| 2:45–3:35 | Repetir código y abrir flow rojo en Prefect | “El segundo uso se bloquea durante 90 segundos en check_anti_replay_cache.” |
| 3:35–4:15 | Login con respaldo y log de estrategia | “Strategy permite intercambiar TOTP por un respaldo de un solo uso.” |
| 4:15–5:00 | Código de estado, cuatro tareas, pruebas y README | “La semilla permanece pendiente hasta verificarla; las pruebas cubren RFC, tokens y replay concurrente.” |

## Preguntas para defender el diseño

- ¿Por qué no basta con la contraseña? Solo confirma el primer factor; el servidor exige un token con otro propósito para el recurso protegido.
- ¿Qué evita un bloqueo durante el alta? El estado pendiente solo pasa a activo al demostrar que se importó correctamente la semilla.
- ¿Por qué C−1 y C+1? Permiten un desfase de una ventana sin ampliar indefinidamente la validez.
- ¿Qué pasa con dos solicitudes simultáneas? Un bloqueo del pipeline y una transacción de consumo garantizan una aceptación por proceso.
- ¿Por qué no registrar el código? Los logs deben revelar decisiones y fallos sin convertirse en un almacén de credenciales.
- ¿Funciona en varios workers? No en esta PoC; requiere un mecanismo compartido de consumo y bloqueo.

## Publicar la evidencia

Sube la grabación al servicio elegido y comprueba que el docente pueda verla. Sustituye “pendiente” por el enlace real tanto aquí como en la sección de video del README. Añade marcas de tiempo reales y el commit demostrado. No subas videos pesados ni credenciales al repositorio. No marques un ensayo como aprobado si no se mostró.

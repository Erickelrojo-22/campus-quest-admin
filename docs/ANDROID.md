# Android conectado a Render

Proyecto: `/home/elkindev/AndroidStudioProjects/Gamequest`.
La URL de producción está en `app/build.gradle.kts`:
`https://campus-quest-api-prod.onrender.com/api/v1/`.

## Funcionamiento

- `AppContainer` inyecta `CampusApi`, `SessionTokenStore` y `RemoteCampusRepository`.
- Registro institucional: `POST auth/register`, cuenta estudiante, contraseña de
  al menos 8 caracteres. El correo tiene formato institucional; esta versión
  no verifica la propiedad del correo ni incluye recuperación de contraseña.
- Login: `POST auth/login`, con contraseña sin recortar espacios.
- Acceso rápido: `POST auth/visitor`, crea una cuenta nueva. El nombre nunca
  permite recuperar una cuenta ajena. La sesión del visitante dura 24 horas;
  al cerrar sesión o expirar no se puede recuperar sin credenciales.
- Token Bearer cifrado con AES/GCM y una clave Android Keystore. No se
  almacenan contraseñas en la caché remota.
  [Referencia Android Keystore](https://developer.android.com/privacy-and-security/keystore).
- Catálogo: `GET puntos` y `GET catalogo`, incluyendo misiones archivadas
  que el usuario ya completó para reconstruir sus insignias e historial.
- Progreso: `GET/POST usuarios/{id}/progreso`. El servidor valida el QR y
  calcula fecha, puntos y nivel; las peticiones repetidas no duplican puntos.
- Ranking: `GET ranking`, solo nombres, IDs, puntos y niveles; no expone correos.
- Room conserva la última descarga en `campus_quest_remote.db`. La app
  actualiza al abrirse y cada 30 segundos mientras está visible.
- Sin conexión se puede leer la caché; completar misiones requiere conexión.
  No existe todavía una cola de completaciones pendientes.
- Logout borra el token local e intenta revocarlo en el servidor. Un 401
  elimina la sesión y devuelve al login.
- El catálogo se administra desde la web; Android no concede permisos tutor.

## Datos anteriores del teléfono

La antigua base `campus_quest.db` se conserva sin modificar. Sus usuarios,
contraseñas y progreso no se copian automáticamente al servidor. Los IDs
locales no identifican cuentas remotas. Para migrarlos hay que verificar la
identidad, definir qué historial se acepta y mapear cada usuario y misión.
La sesión antigua de DataStore no se acepta como autenticación remota.

## Compilar

```bash
./gradlew :app:assembleDebug :app:testDebugUnitTest
```

El APK se genera en `app/build/outputs/apk/debug/app-debug.apk`.
La app usa exclusivamente HTTPS y el permiso INTERNET; no necesita
`adb reverse` ni acceso directo a PostgreSQL.

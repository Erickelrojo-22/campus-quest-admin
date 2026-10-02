# Android: integración en la siguiente etapa

Repositorio analizado: `/home/elkindev/AndroidStudioProjects/Gamequest`.
Actualmente usa Kotlin, Compose, Room y DataStore. `AppContainer.kt` inyecta
repositorios locales; no hay cliente HTTP, permiso INTERNET ni backend remoto
integrado. **Esta entrega no modifica ese proyecto**.

`docs/BACKEND.md` del proyecto Android proponía un servidor compartido. Ahora
este repositorio implementa la primera API y documenta su contrato; la app
móvil todavía necesita una capa remota.

## Direcciones para probar después

| Entorno | URL base |
|---|---|
| Emulador Android Studio | `http://10.0.2.2:8000/api/v1/` |
| Dispositivo USB con adb reverse | `http://127.0.0.1:8000/api/v1/` |
| Dispositivo en la misma red | `http://IP_DEL_EQUIPO:8000/api/v1/` |
| Producción | `https://tu-backend.up.railway.app/api/v1/` |

`10.0.2.2` es el alias al loopback del ordenador anfitrión; `localhost` dentro
del emulador se refiere al propio Android. Véase
[documentación de red del emulador](https://developer.android.com/studio/run/emulator-networking-address).
Para probar por LAN, inicia Uvicorn con `--host 0.0.0.0` y permite el puerto en
el firewall. Compose lo publica solo en localhost por defecto.

Con USB:

```bash
adb devices
adb reverse tcp:8000 tcp:8000
adb reverse --list
```

Para retirar la redirección:

```bash
adb reverse --remove tcp:8000
```

## Plan de implementación

1. Definir registro institucional, recuperación de cuenta y acceso de visitante.
   El MVP no incluye esos endpoints: no inventar registro en el cliente.
2. Agregar permiso INTERNET y Retrofit/OkHttp o Ktor en Android.
3. Crear DTOs remotos con los mismos campos camelCase del [contrato](API.md).
4. Agregar un `ApiService`, almacenamiento protegido del token y manejo de
   expiración 401. No tratar el ID local DataStore como autenticación remota.
5. Inyectar el cliente en `AppContainer.kt`.
6. Adaptar `AuthRepository` y `CampusRepository` para coordinar HTTP y Room.
7. Guardar el catálogo remoto en Room y mantener las pantallas leyendo sus Flow,
   de modo que Room actúe como caché y la UI siga disponible sin conexión.
8. Crear una cola de completaciones pendientes, reenviar al recuperar la red y
   marcar una recompensa como confirmada cuando el servidor la acepte.
9. Migrar usuarios/IDs locales a IDs del servidor y resolver cuentas existentes
   antes de sincronizar progreso. No unir personas solo por nombre.
10. Retirar gestión administrativa móvil según la decisión de roles: admin web,
    estudiante/visitante móvil. El rol `tutor` actual no equivale a admin remoto.

## Firma conceptual del servicio

Ejemplo de interfaces para la próxima implementación; **no están añadidas al
repositorio Android**:

```kotlin
interface CampusApi {
    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("auth/me")
    suspend fun me(): UsuarioDto

    @GET("puntos")
    suspend fun puntos(): List<PuntoInteresDto>

    @GET("misiones")
    suspend fun misiones(): List<MisionDto>

    @GET("usuarios/{id}/progreso")
    suspend fun progreso(@Path("id") usuarioId: Int): List<ProgresoDto>

    @POST("usuarios/{id}/progreso")
    suspend fun completar(
        @Path("id") usuarioId: Int,
        @Body body: CompletarRequest
    ): ProgresoDto
}
```

Usa una base URL terminada en `/api/v1/`; el interceptor añade
`Authorization: Bearer <accessToken>` excepto al login. `fechaHora` se mapea a
`Long`, y los IDs/puntos se mantienen compatibles con `Int`. Consultar el
progreso de otro estudiante devolverá 403.

Al completar se envía `{misionId, codigoQr}`. El servidor calcula fecha,
puntos y nivel. Repetir la petición devuelve el mismo evento; no sumar puntos
por cada intento de sincronización. Una misión archivada conserva su evento
previo, aunque ya no aparezca en el catálogo activo: el móvil debe conservar
los detalles cacheados del historial. Si necesita reconstruir desde cero
el detalle de misiones archivadas, definir un endpoint personal de historial
con los detalles del catálogo; la API actual devuelve IDs y no permite a un
estudiante solicitar `incluirArchivadas=true`.

## HTTP de desarrollo y HTTPS real

Agrega `android.permission.INTERNET`. Android moderno bloquea HTTP claro por
defecto: habilítalo únicamente en la variante debug con una configuración de
seguridad de red de desarrollo. Mantén HTTPS en release y no amplíes esa
excepción a producción. Véase [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config).

No importar automáticamente hashes o sesiones locales: el backend debe
verificar identidades y establecer sesiones remotas. Las contraseñas backend
conservan los espacios; revisar la transición porque el login Android actual
usa trim. También debe definirse cómo se migran puntuaciones ya acumuladas
localmente sin aceptar totales manipulables desde el cliente.

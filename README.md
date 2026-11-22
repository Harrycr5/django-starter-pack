# Django Starter Pack

API REST en Django 5.2 y Django REST Framework, con JWT y perfiles de Django. El frontend vive en su propio repositorio.

## Estructura

- `core/` es el proyecto Django. Los settings están en `core/settings/` y la URLconf principal en `core/urls.py`.
- `apps/common/` contiene los componentes reutilizables y el comando `startmodule`.
- `apps/accounts/` contiene `accounts.User`, JWT, perfiles, menú y recuperación.
- `tests/` contiene las pruebas de la API y los modelos.

`core/routing.py` descubre los `urls.py` de los paquetes directos en `apps/` y monta sus `urlpatterns` bajo `/api/`.

## Arranque local

Usa Python 3.12 o superior dentro del rango compatible con Django 5.2. En PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Configura DATABASE_URL en .env con tu usuario y base PostgreSQL.
python manage.py makemigrations
python manage.py migrate
python manage.py setup_profiles
python manage.py createsuperuser
python manage.py runserver
```

En Linux o macOS, usa `python3.12 -m venv .venv`, `source .venv/bin/activate` y `cp .env.example .env`. Las migraciones se generan localmente y Git solo conserva `migrations/__init__.py`. Configura `DATABASE_URL` con una base PostgreSQL existente antes de inicializar el proyecto. Desarrollo muestra el correo en consola, incluidos los códigos de recuperación.

Swagger UI está en `http://localhost:8000/api/docs/` y el esquema OpenAPI en JSON en `/api/schema/`. Todas las rutas tienen barra final. Las respuestas con estado 204 llevan el cuerpo vacío. Los errores de la API usan `{"error":{"status":400,"details":{}}}`.

El usuario personalizado se registra como `accounts.User`. Si ya tienes una base en uso, conserva su historial local de migraciones para aplicar cambios incrementales. El usuario y los modelos que heredan de `BaseModel` usan UUID v4 como clave primaria. La API devuelve los UUID como cadenas.

## Autenticación

Todas las rutas de esta tabla parten de `/api/auth/`. Los campos de fecha de la API aceptan `DD/MM/YYYY`, `YYYY/MM/DD` y `YYYY-MM-DD`. La API devuelve `YYYY-MM-DD`. `createsuperuser` solicita correo, usuario, nombres, fecha de nacimiento y contraseña.

| Método y ruta | Datos o resultado |
| --- | --- |
| POST `register/` | `username`, `email`, `first_name`, `last_name`, `birth_date`, `password`, `password2`. Asigna el perfil Usuario. |
| POST `login/` | `email` o `username`, junto con `password`. Devuelve `access` y `refresh`. |
| POST `refresh/` | `refresh`. Devuelve ambos tokens nuevos e invalida el refresh anterior. |
| POST `logout/` | `refresh`. Invalida ese refresh. El access dura hasta su vencimiento. |
| GET/PATCH `me/` | Requiere Bearer. Devuelve datos, grupos, permisos e `is_superuser`. PATCH admite nombres y fecha de nacimiento. |
| GET `me/menu/` | Requiere Bearer. Devuelve el menú y sus hijos filtrados por permisos. |
| POST `change-password/` | Requiere Bearer, `current_password` y `password`. Revoca sesiones. |
| POST `forgot-password/` | `email`. La respuesta es la misma para cualquier correo válido. |
| POST `verify-code/` | `email` y `code`. Validación opcional antes del reset. Los intentos fallidos cuentan para el mismo límite. |
| POST `reset-password/` | `email`, `code` como cadena de seis dígitos y `password`. Consume el código y revoca sesiones. |
| POST `verify-email/` | `token` recibido por correo cuando `REQUIRE_EMAIL_VERIFICATION=True`. |

## Administración desde React

Estas rutas requieren Bearer, perfil Administrador o superusuario, y el permiso de Django correspondiente. Los listados son paginados y devuelven `count`, `next`, `previous` y `results`.

| Recurso | Rutas y operaciones |
| --- | --- |
| Usuarios | `GET /api/users/`, `GET /api/users/{uuid}/` y `PATCH /api/users/{uuid}/` con `{"groups": [id]}` para reemplazar los perfiles asignados. El registro sigue en `/api/auth/register/`. |
| Perfiles | `GET` y `POST /api/profiles/`. `GET`, `PATCH`, `PUT` y `DELETE /api/profiles/{id}/` para perfiles personalizados. El cuerpo admite `name` y `permissions` como lista de IDs. |
| Permisos | `GET /api/permissions/` y `GET /api/permissions/{id}/`. Cada permiso incluye `id`, `name`, `app_label`, `model`, `codename` y `key` con formato `app_label.codename`. |

Los perfiles del sistema se sincronizan desde `apps/accounts/profiles.py`. Solo un superusuario puede asignar el perfil Administrador o cambiar los perfiles de otro administrador o superusuario. `/api/auth/me/menu/` incluye las secciones administrativas según el perfil y los permisos efectivos.

## Consumir desde React

Vite en `http://localhost:5173` y React en `http://localhost:3000` tienen acceso CORS en desarrollo. El cliente envía `Authorization: Bearer <access>`. Coloca este ejemplo en el repositorio React. Los tokens quedan en memoria, así que recargar la página requiere iniciar sesión otra vez.

```js
const api = "http://localhost:8000/api/auth/";
let tokens;
let refreshing;

async function post(path, body) {
  const response = await fetch(api + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function login(email, password) {
  tokens = await post("login/", { email, password });
}

async function getAuthenticated(path) {
  if (!tokens) throw new Error("Inicia sesión");
  const access = tokens.access;
  const get = (token) => fetch(api + path, {
    headers: { Authorization: `Bearer ${token}` },
  });

  let response = await get(access);
  if (response.status === 401) {
    if (!tokens) throw new Error("La sesión venció");
    if (tokens.access === access) {
      // Las solicitudes concurrentes comparten una sola rotación.
      refreshing ??= post("refresh/", { refresh: tokens.refresh })
        .then((next) => { tokens = next; })
        .catch((error) => { tokens = undefined; throw error; })
        .finally(() => { refreshing = undefined; });
      await refreshing;
    }
    response = await get(tokens.access);
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export function loadSession() {
  return Promise.all([getAuthenticated("me/"), getAuthenticated("me/menu/")]);
}

// En el submit del formulario:
// await login(email, password);
// const [me, menu] = await loadSession();
```

### Vistas, navegación y botones

Guarda el resultado de `loadSession()` en un contexto de React o en el estado de sesión que ya uses. `me` contiene la identidad y los permisos efectivos. `menu` es el árbol de navegación visible para esa sesión. La API filtra cada nivel por permiso. Si un padre requiere un permiso que el usuario no tiene, se omite toda su rama.

Cada nodo del menú incluye `label` para el texto, `path` para la ruta React, `icon` como clave del icono, `permission` para el permiso requerido y `children` para los nodos anidados. Un nodo con `path: null` puede servir como encabezado de sección. Las rutas apuntan a pantallas registradas en React. Por ejemplo, `/perfiles` carga la vista de perfiles y esa vista consulta `/api/profiles/`.

El siguiente ejemplo recibe el componente `Link` del router de tu aplicación. Usa el mismo árbol para el menú lateral y para proteger las pantallas principales al entrar desde un enlace directo.

```jsx
function NavTree({ nodes, Link, icons = {} }) {
  if (!nodes.length) return null;

  return (
    <ul>
      {nodes.map(({ label, path, icon, children }) => {
        const Icon = icons[icon];
        const title = <>{Icon && <Icon aria-hidden="true" />} {label}</>;

        return (
          <li key={path ?? label}>
            {path ? <Link to={path}>{title}</Link> : <span>{title}</span>}
            <NavTree nodes={children} Link={Link} icons={icons} />
          </li>
        );
      })}
    </ul>
  );
}

function hasMenuPath(nodes, path) {
  return nodes.some((node) =>
    node.path === path || hasMenuPath(node.children, path)
  );
}

function ProfilesRoute({ session, onCreateProfile }) {
  const { me, menu } = session;
  if (!hasMenuPath(menu, "/perfiles")) return <p>Acceso denegado.</p>;

  const canCreate = me.permissions.includes("auth.add_group");
  return (
    <section>
      <h1>Perfiles</h1>
      {canCreate && <button onClick={onCreateProfile}>Crear perfil</button>}
      {/* Renderiza aquí el listado paginado de GET /api/profiles/. */}
    </section>
  );
}
```

Para rutas de detalle como `/perfiles/:id`, aplica el guard de la sección `/perfiles` y consulta el recurso por ID. `children` organiza la navegación. Los botones consultan `me.permissions` con la clave de la acción:

| Pantalla | Botón o acción | Permiso |
| --- | --- | --- |
| Mi perfil | Guardar mis datos | `accounts.change_user` |
| Usuarios | Cambiar los perfiles de un usuario | `accounts.change_user` |
| Perfiles | Crear perfil | `auth.add_group` |
| Perfiles | Editar perfil | `auth.change_group` |
| Perfiles | Eliminar perfil | `auth.delete_group` |
| Perfiles | Cargar el catálogo para elegir permisos | `auth.view_permission` |

Las acciones administrativas requieren acceso a la sección y el permiso indicado. La API también valida restricciones del recurso, como los perfiles reservados y quién puede asignar el perfil Administrador. Si una operación devuelve `403`, muestra el acceso denegado. Si un `401` persiste tras intentar refrescar el token, vuelve al login. Cuando cambien los permisos o perfiles de la cuenta activa, vuelve a cargar `me` y `menu` para actualizar la pantalla.

## Cómo crear un módulo nuevo

- [ ] Ejecuta `python manage.py startmodule nombre` para crear la app. Añade `apps.nombre.apps.ModuleConfig` a `INSTALLED_APPS` en `core/settings/base.py` si vas a usar modelos.
- [ ] Hereda de `apps.common.models.BaseModel`, declara `uppercase_fields` y usa `UppercaseSerializerMixin`.
- [ ] Usa `BaseViewSet` con `Modelo.all_objects` y exporta `urlpatterns` en `apps/nombre/urls.py`. Para activar paginación, asigna `StandardPagination` al viewset. Activa `allow_restore` si necesitas restauración.
- [ ] Para datos privados, usa `OwnObjectPermission`, declara `owner_field` y restringe el queryset de listado.
- [ ] Ejecuta `python manage.py makemigrations` y `python manage.py migrate`. Configura los permisos en `apps/accounts/profiles.py` y el menú en `apps/accounts/menu.py`.
- [ ] Ejecuta `python manage.py setup_profiles` y prueba el acceso con y sin permiso.

## Producción y límites

- Usa `--settings=core.settings.prod` para comandos de gestión o configura `DJANGO_SETTINGS_MODULE=core.settings.prod` en el entorno del servidor. Define `SECRET_KEY`, `JWT_SIGNING_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, los orígenes CORS autorizados y las variables SMTP de `.env.example`. El perfil de producción fuerza HTTPS.
- Define `CACHE_URL=redis://...` para compartir los límites de frecuencia entre procesos. El caché local sirve para desarrollo. Programa `python manage.py flushexpiredtokens` para retirar tokens vencidos.
- `setup_profiles` sincroniza exactamente los permisos de los grupos gestionados. Para asignaciones manuales persistentes, usa permisos directos o grupos adicionales. El superusuario recibe sus permisos por Django.
- En cuentas, `is_active=False` bloquea la autenticación. El usuario conserva un manager capaz de consultar cuentas inactivas y se gestiona aparte del borrado lógico de los modelos de negocio.
- `bulk_create()`, `update()` y `bulk_update()` omiten el `save()` del modelo. Aplica `normalize_uppercase` explícitamente en escrituras masivas y pasa los datos de auditoría que correspondan. El borrado lógico conserva relaciones. Un borrado físico en cascada puede eliminar registros asociados.
- PostgreSQL proporciona bloqueo de fila para recuperación y rotación concurrentes. El correo se envía tras confirmar la transacción y el tiempo de respuesta puede depender del servidor SMTP.
- Los perfiles se administran con el comando de sincronización o `python manage.py shell`. Swagger UI usa la vista incluida en drf-spectacular. El correo de recuperación se compone en el servicio y se envía como texto plano. Los formularios y clases de admin son componentes opcionales sin rutas web.

## Comprobaciones

El workflow `.github/workflows/ci.yml` ejecuta las comprobaciones con PostgreSQL en cada push y pull request. Genera las migraciones en el runner antes de probar.

En un clon nuevo, ejecuta `python manage.py makemigrations` antes de correr las pruebas. Las pruebas usan una base PostgreSQL temporal. El usuario configurado en `DATABASE_URL` necesita permiso para crear la base de pruebas.

```sh
python -m pytest -q
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn
```

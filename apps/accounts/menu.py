MENU = [
    {
        "label": "Mi perfil", "path": "/perfil", "icon": "user",
        "permission": "accounts.view_user", "children": [],
    },
]


ADMIN_MENU = [
    {"label": "Usuarios", "path": "/usuarios", "icon": "users", "permission": "accounts.view_user", "children": []},
    {"label": "Perfiles", "path": "/perfiles", "icon": "shield", "permission": "auth.view_group", "children": []},
    {"label": "Permisos", "path": "/permisos", "icon": "key", "permission": "auth.view_permission", "children": []},
]

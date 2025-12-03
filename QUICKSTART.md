# ✅ Docker Packaging Complete

## Lo que hemos hecho

Se ha **empaquetado completamente** la aplicación Backup_Script para ejecutarse en Docker. Aquí está lo que se agregó/modificó:

### 📦 Nuevos Archivos Creados

| Archivo | Propósito |
|---------|-----------|
| `Dockerfile` | Define cómo construir la imagen Docker (incluye Python, binarios, deps) |
| `.dockerignore` | Excluye archivos innecesarios del build (backups, logs, config, etc.) |
| `scripts/run_backup_docker.ps1` | ⭐ **Script PowerShell** que ejecuta backups de forma segura (solicita contraseña, limpia variables) |
| `DOCKER.md` | Guía completa sobre Docker (qué es, cómo funciona, troubleshooting) |
| `SETUP_GUIDE.md` | **Guía de inicio rápido** (2 opciones: Docker o instalación local) |
| `config/example.env` | Plantilla de variables de entorno (no contiene secretos reales) |

### 📝 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `README.md` | Añadida sección Docker explicando qué es, cómo construir, seguridad |
| `makefile` | Nuevos targets: `build-image`, `build-image-full`, `push-image`, `clean-docker`, `docker-help` |
| `.gitignore` | Actualizado para excluir backups, config, secretos, logs |
| `src/utils/notify.py` | Soporte para tokens Bearer (además de JWT) |
| `src/cli/config_cmd.py` | Comandos `notify-auth-set` y `notify-auth-show` (gestión segura de secretos) |
| `src/cli/backup_cmd.py` | Integración con auth por env/prompt (sin almacenar secretos en config) |

---

## 🚀 Cómo Empezar

**⏱️ Tiempo total: ~30 minutos (solo la primera vez)**

Sigue la **guía paso a paso** completa en **`DOCKER_PASO_A_PASO.md`**:

- ✅ Descargar e instalar Docker
- ✅ Construir imagen
- ✅ Ejecutar primer backup
- ✅ Verificar archivos guardados
- ✅ Troubleshooting y FAQ

**Resumen rápido**:
```powershell
# 1. Construir imagen (una sola vez, ~5 min)
make build-image

# 2. Ejecutar backup
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres
#    Script solicita contraseña (sin mostrar)

# 3. Verificar
ls .\backups
```

**Para la guía completa** → Abre `DOCKER_PASO_A_PASO.md`

**Resultado**: Archivo de backup en `./backups/` + entrada en `backup_history.json`

---

## 📋 Opciones de Línea de Comandos (Script PowerShell)

```powershell
.\scripts\run_backup_docker.ps1 -DbType <tipo> -Database <db> -User <user> [opciones]

Parámetros:
  -DbType              postgres | mysql | mongo | sqlserver (REQUERIDO)
  -Database            Nombre de la base de datos (REQUERIDO)
  -User                Usuario para conectar (REQUERIDO)
  -Host                Host de la BD (default: host.docker.internal)
  -Port                Puerto (default: según DbType)
  -Compress            zip | tar | gz | none (opcional)
  -Cloud               s3 | gcs | azure (opcional, requiere config)
  -NotifySlack         Enviar notificación webhook después
  -SkipBinaryCheck     No verificar binarios
  -ImageName           Nombre de imagen (default: backup_script)
  -ImageTag            Tag (default: local)

Ejemplos:
  .\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres
  .\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress zip
  .\scripts\run_backup_docker.ps1 -DbType mongo -Database Algoritmo -User admin -NotifySlack
```

---

## 🏗️ ¿Cómo funciona internamente?

```
Tu PC                           Docker Container
┌─────────────────┐            ┌─────────────────────────────┐
│ run_backup...   │            │                             │
│   .ps1 script   │            │  Python 3.11 + Linux        │
│                 │ ─────┐     │  ├─ psql (postgres)         │
│ • Pide password │      │     │  ├─ mysql client            │
│ • $env:PGPASS.. │      └────→│  ├─ mongosh                 │
│ • docker run    │            │  ├─ dependencias Python     │
│ • limpia vars   │            │  ├─ código backup_script    │
└─────────────────┘            │  │                          │
                               │  └─ Ejecuta backup          │
                               │     (psql, mysqldump, etc)  │
                               └─────────────────────────────┘
                                      │
                                      │ Mapea ./backups
                                      ↓
                               Tu PC: ./backups/
                               postgres_mydb_...dump
                               mysql_mydb_...sql
```

---

## 🔐 Seguridad: Cómo se manejan las contraseñas

### ✅ Proceso Seguro (lo que hace el script)

```
1. Read-Host -AsSecureString          ← Pide contraseña sin eco
2. docker run -e PGPASSWORD=...       ← Inyecta solo al contenedor
3. Remove-Item Env:PGPASSWORD         ← Limpia después
```

✅ La contraseña **nunca**:
- Aparece en pantalla
- Se escribe en archivos
- Queda en historial de PowerShell
- Aparece en procesos visibles

❌ Nunca hagas:
```powershell
# MALO: aparece en historial
docker run backup_script:local backup run --password "MiPassword123" ...
```

---

## 🌍 Subir a Docker Hub (Opcional)

Para compartir la imagen:

```powershell
# 1. Crear repo en https://hub.docker.com

# 2. Login
docker login
# Pide usuario/contraseña

# 3. Tag
docker tag backup_script:local tusuario/backup_script:latest

# 4. Push
docker push tusuario/backup_script:latest

# Otros usuarios pueden descargar:
docker pull tusuario/backup_script:latest
```

---

## 📚 Documentación

Léela en orden de profundidad:

1. **SETUP_GUIDE.md** ← Empieza aquí (guía rápida)
2. **README.md** → Todos los comandos y ejemplos
3. **DOCKER.md** → Cómo funciona Docker, troubleshooting

---

## ✨ Características Incluidas

✅ **Dockerfile** con clientes comunes (postgres, mysql)
✅ **Script PowerShell** seguro para ejecutar backups
✅ **Notificaciones webhook** con autenticación segura (JWT/Bearer)
✅ **Documentación completa** en 3 niveles
✅ **Makefile targets** para build, push, limpieza
✅ **`.gitignore` y `example.env`** para seguridad
✅ **Variables de entorno** inyectadas en runtime (no en config)

---

## 🛠️ Comandos Útiles

```powershell
# Build
make build-image           # Imagen básica (postgres, mysql)
make build-image-full      # Imagen completa (+ mongodb)

# Ver ayuda
make docker-help

# Ejecutar backup (recomendado)
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# Debug/shell interactivo
docker run -it backup_script:local bash

# Limpiar
make clean-docker          # Remove containers/images

# Push a Docker Hub
docker login
docker tag backup_script:local tu_usuario/backup_script:latest
docker push tu_usuario/backup_script:latest
```

---

## ⚠️ Notas Importantes

1. **`host.docker.internal`**: Dentro del contenedor, usa esto para conectar a BD locales (no `localhost`).
2. **Tamaño de imagen**: ~600-800 MB con clientes comunes. Puede crecer a ~1 GB con MongoDB/SQL Server tools.
3. **Almacenamiento de secretos**: Nunca guardes contraseñas en `config.toml`. Usa variables de entorno o el script que solicita en runtime.
4. **Seguridad**: El script limpia variables sensibles después de ejecutar. Siempre úsalo o sigue el patrón "solicitar → inyectar → limpiar".

---

## 🚀 Próximos Pasos

- [ ] Instalar Docker Desktop
- [ ] Ejecutar `make build-image`
- [ ] Ejecutar script PowerShell con un backup de prueba
- [ ] Revisar `backup_history.json` para confirmar registro
- [ ] Configurar notificaciones si la necesitas
- [ ] Compartir imagen en Docker Hub (opcional)

**¡Listo! Tu aplicación está completamente empaquetada y lista para producción.** 🎉

# 📚 Índice de Documentación

Bienvenido. Aquí encontrarás todos los documentos disponibles organizados por nivel de detalle.

---

## 🚀 Empieza Por Aquí

Si es tu **primera vez** usando esta aplicación:

1. **`DOCKER_PASO_A_PASO.md`** ← **LEE ESTO PRIMERO** 
   - Desde cero: instalar Docker, construir imagen, ejecutar backup
   - Paso a paso detallado
   - Troubleshooting incluido

2. **`QUICKSTART.md`** (resumen visual)
   - Vista general (5 minutos)
   - Características principales
   - Próximos pasos

---

## 📖 Documentación Completa

| Documento | Para Quién | Contenido |
|-----------|-----------|----------|
| **DOCKER_PASO_A_PASO.md** | Usuarios nuevos | Instalación Docker → Primer backup paso a paso |
| **QUICKSTART.md** | Resumen visual | Características, comandos útiles, próximos pasos |
| **SETUP_GUIDE.md** | Instalación | 2 opciones: Docker o instalación local; preguntas frecuentes |
| **DOCKER.md** | Usuarios avanzados | Cómo funciona Docker, arquitecturas, optimización |
| **README.md** | Referencia completa | Todos los comandos CLI, ejemplos, webhooks, restauración |
| **INDEX.md** | Este archivo | Tabla de contenidos, dónde buscar |

---

## 🎯 Busca Por Necesidad

### "Quiero instalar y ejecutar un backup"

→ **`DOCKER_PASO_A_PASO.md`** (Pasos 1-6)

```powershell
make build-image
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres
```

---

### "Quiero entender cómo funciona Docker"

→ **`DOCKER.md`** (secciones: "¿Qué es Docker?", "Flujo: Build → Run")

---

### "Tengo un error al ejecutar"

→ **`DOCKER_PASO_A_PASO.md`** (sección: "Troubleshooting")

Errores comunes:
- `docker: command not found` → Ver Troubleshooting
- `permission denied` → Ver Troubleshooting
- `container exited with error code 1` → Ver Troubleshooting

---

### "Quiero configurar notificaciones webhook"

→ **`README.md`** (sección: "Notificaciones (Webhook)")

```powershell
python src/cli.py config notify-set --url "https://webhook.example.com/notify"
python src/cli.py config notify-auth-set --method env --token-type jwt --env-var NOTIFY_SECRET
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -NotifySlack
```

---

### "Quiero automatizar backups diarios"

→ **`DOCKER_PASO_A_PASO.md`** (sección: "Ejecutar Backups Regularmente")

Windows:
```powershell
# Task Scheduler
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-File C:\ruta\scripts\run_backup_docker.ps1 ..."
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "DailyBackup" -Action $action -Trigger $trigger
```

Linux/macOS:
```bash
# Cron
0 2 * * * cd /ruta && ./scripts/run_backup_docker.ps1 ...
```

---

### "Quiero ver todos los comandos CLI disponibles"

→ **`README.md`** (secciones: "Ejemplos prácticos de uso")

Ejemplos incluyen:
- Backup (Postgres, MySQL, Mongo, SQL Server)
- Restore (todos los tipos de BD)
- Configuración (database, cloud, webhooks)
- Historial (ver, filtrar, eliminar)
- Utilidades (hash, compress, upload)

---

### "Quiero subir mi imagen a Docker Hub"

→ **`DOCKER_PASO_A_PASO.md`** (sección: "Subir a Docker Hub")

O **`README.md`** (sección: "Docker: construir imagen de la aplicación" → Pushing a Docker Hub)

```powershell
docker login
docker tag backup_script:local usuario/backup_script:latest
docker push usuario/backup_script:latest
```

---

### "¿Cómo manejaré contraseñas de forma segura?"

→ **`DOCKER_PASO_A_PASO.md`** (sección: "Seguridad: ¿Dónde queda la contraseña?")

✅ **Seguro**:
```powershell
$Password = Read-Host -AsSecureString
docker run -e PGPASSWORD=$Password ...
Remove-Item Env:PGPASSWORD
```

❌ **Inseguro** (nunca):
```powershell
docker run ... --password "MiPassword123" ...
```

---

### "Quiero entender la estructura del proyecto"

→ **`SETUP_GUIDE.md`** (sección: "📁 Estructura de Carpetas")

```
Backup_Script_maqueta/
├── Dockerfile              # Empaquetamiento Docker
├── scripts/run_backup...ps1 # Script PowerShell seguro
├── src/cli.py              # Punto de entrada
├── backups/                # Donde se guardan backups
└── ...
```

---

## 📋 Checklist Rápido: "Estoy Listo Para..."

### ✅ Mi primer backup
- [ ] Leo `DOCKER_PASO_A_PASO.md` (Pasos 1-6)
- [ ] Instalo Docker
- [ ] Ejecuto `make build-image`
- [ ] Ejecuto script PowerShell
- [ ] Veo archivo en `./backups`

### ✅ Automatizar backups
- [ ] Ejecuto un backup manual (arriba)
- [ ] Leo `DOCKER_PASO_A_PASO.md` sección "Automatización"
- [ ] Configuro Task Scheduler o Cron

### ✅ Configurar notificaciones
- [ ] Leo `README.md` sección "Notificaciones"
- [ ] Ejecuto comandos `config notify-set` y `notify-auth-set`
- [ ] Añado `-NotifySlack` al script PowerShell

### ✅ Usar en producción
- [ ] Ejecuto backups manuales (prueba)
- [ ] Automatienzo con Task Scheduler / Cron
- [ ] Configuro notificaciones webhook
- [ ] Subo imagen a Docker Hub (opcional)
- [ ] Documento en tu wiki/runbook

---

## 🗂️ Mapa de Documentos

```
Nivel Principiante
    ↓
DOCKER_PASO_A_PASO.md
    ↓
Nivel Intermedio
    ↓
QUICKSTART.md → SETUP_GUIDE.md → DOCKER.md
    ↓
Nivel Avanzado
    ↓
README.md (referencia completa)
```

---

## 🎓 Ejemplos por Tipo de BD

### PostgreSQL

```powershell
# Básico
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres

# Con compresión
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -Compress zip

# Con notificación
.\scripts\run_backup_docker.ps1 -DbType postgres -Database mydb -User postgres -NotifySlack
```

Ver más en: **`README.md`** sección "1) Backup — Ejemplo"

---

### MySQL

```powershell
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root

# Con compresión
.\scripts\run_backup_docker.ps1 -DbType mysql -Database mydb -User root -Compress tar
```

Ver más en: **`README.md`** sección "1) Backup — Ejemplo"

---

### MongoDB

```powershell
.\scripts\run_backup_docker.ps1 -DbType mongo -Database mydb -User admin

# Con notificación
.\scripts\run_backup_docker.ps1 -DbType mongo -Database mydb -User admin -NotifySlack
```

Ver más en: **`README.md`** sección "1) Backup — Ejemplo"

---

### SQL Server

```powershell
.\scripts\run_backup_docker.ps1 -DbType sqlserver -Database mydb -User sa
```

Ver más en: **`README.md`** sección "1) Backup — Ejemplo"

---

## ❓ Preguntas Frecuentes

**P: ¿Por dónde empiezo?**  
R: Lee `DOCKER_PASO_A_PASO.md` (Paso 1)

**P: ¿Qué pasa si tengo un error?**  
R: Ve a `DOCKER_PASO_A_PASO.md` sección "Troubleshooting"

**P: ¿Dónde veo todos los comandos disponibles?**  
R: `README.md` sección "Ejemplos prácticos de uso"

**P: ¿Cómo automatizo backups diarios?**  
R: `DOCKER_PASO_A_PASO.md` sección "Ejecutar Backups Regularmente"

**P: ¿Es seguro guardar mi contraseña?**  
R: No. El script la solicita en runtime. Ver `DOCKER_PASO_A_PASO.md` sección "Seguridad"

---

## 🔗 Enlaces Rápidos

| Tarea | Documento | Sección |
|------|-----------|---------|
| Instalar Docker | DOCKER_PASO_A_PASO.md | Paso 1 |
| Construir imagen | DOCKER_PASO_A_PASO.md | Paso 3 |
| Primer backup | DOCKER_PASO_A_PASO.md | Paso 5 |
| Troubleshooting | DOCKER_PASO_A_PASO.md | Troubleshooting |
| Seguridad | DOCKER_PASO_A_PASO.md | Seguridad |
| Comandos CLI | README.md | Ejemplos prácticos |
| Webhooks | README.md | Notificaciones |
| Automatización | DOCKER_PASO_A_PASO.md | Ejecutar Regularmente |

---

## 📞 Soporte

Si tienes dudas:

1. **Primero**: Busca en el documento relevante
2. **Segundo**: Revisa `DOCKER_PASO_A_PASO.md` sección "Troubleshooting"
3. **Tercero**: Verifica `README.md` en la sección del comando que usas

**¡Listo! Comienza por `DOCKER_PASO_A_PASO.md` 🚀**

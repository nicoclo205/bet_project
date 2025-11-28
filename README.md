# Bet Project - Back-end Django

Sistema de apuestas deportivas multideporte con Django REST Framework.

## Requisitos Previos

- Docker (versión 20.10 o superior)
- Docker Compose (versión 1.29 o superior)

## Configuración Inicial

### 1. Clonar el repositorio y navegar al directorio

```bash
cd bet_project
```

### 2. Crear archivo de variables de entorno

Copia el archivo `.env.example` a `.env` y ajusta los valores según tus necesidades:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones:

```env
DEBUG=True
SECRET_KEY=tu-secret-key-aqui
DB_PASSWORD=tu-password-segura
DB_ROOT_PASSWORD=tu-root-password-segura
```

**IMPORTANTE**: Cambia las contraseñas por defecto por unas seguras en producción.

## Uso con Docker

### Levantar los servicios (MySQL + Django)

```bash
docker-compose up -d
```

Este comando:
- Descarga las imágenes de MySQL 8.0 y Python 3.11
- Crea un volumen persistente para MySQL (`mysql_data`)
- Levanta el contenedor de base de datos
- Construye la imagen de Django
- Ejecuta las migraciones automáticamente
- Inicia el servidor Django en `http://localhost:8000`

### Ver los logs

```bash
# Ver todos los logs
docker-compose logs -f

# Ver logs solo de Django
docker-compose logs -f web

# Ver logs solo de MySQL
docker-compose logs -f db
```

### Detener los servicios

```bash
# Detener sin eliminar contenedores
docker-compose stop

# Detener y eliminar contenedores (mantiene los datos en el volumen)
docker-compose down

# Detener, eliminar contenedores Y volúmenes (BORRA TODOS LOS DATOS)
docker-compose down -v
```

### Ejecutar comandos Django dentro del contenedor

```bash
# Crear migraciones
docker-compose exec web python manage.py makemigrations

# Aplicar migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Abrir shell de Django
docker-compose exec web python manage.py shell

# Ejecutar tests
docker-compose exec web python manage.py test
```

### Acceder a MySQL directamente

```bash
# Conectarse a MySQL desde el contenedor
docker-compose exec db mysql -u nico -p bet_db

# O como root
docker-compose exec db mysql -u root -p
```

### Reconstruir la imagen de Django

Si modificas el `Dockerfile` o `requirements.txt`:

```bash
docker-compose up -d --build
```

## Estructura de Volúmenes Persistentes

- **mysql_data**: Almacena todos los datos de la base de datos MySQL
- **static_volume**: Archivos estáticos de Django
- **media_volume**: Archivos media subidos por usuarios

Los datos en estos volúmenes persisten incluso si eliminas los contenedores.

## Endpoints Principales

Una vez levantado el servidor, la API estará disponible en:

- **API Root**: http://localhost:8000/api/
- **Panel Admin**: http://localhost:8000/admin/
- **Login**: http://localhost:8000/login/
- **API Auth**: http://localhost:8000/api-auth/

### Endpoints de la API

- `/api/usuarios/` - Gestión de usuarios
- `/api/salas/` - Gestión de salas
- `/api/partidos/` - Partidos de fútbol
- `/api/apuestas-futbol/` - Apuestas de fútbol
- `/api/rankings/` - Rankings por sala
- `/api/mensajes-chat/` - Mensajes de chat

Consulta la documentación de la API navegando a http://localhost:8000/api/

## Desarrollo Local (sin Docker)

Si prefieres desarrollar sin Docker:

### 1. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar base de datos local

Instala MySQL localmente y crea la base de datos:

```sql
CREATE DATABASE bet_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'nico'@'localhost' IDENTIFIED BY 'C0r4z0n#25';
GRANT ALL PRIVILEGES ON bet_db.* TO 'nico'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Configurar .env

Cambia `DB_HOST=db` por `DB_HOST=localhost` en tu archivo `.env`

### 5. Ejecutar migraciones y servidor

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Backup de la Base de Datos

### Crear backup

```bash
docker-compose exec db mysqldump -u nico -p bet_db > backup_$(date +%Y%m%d).sql
```

### Restaurar backup

```bash
docker-compose exec -T db mysql -u nico -p bet_db < backup_20250127.sql
```

## Troubleshooting

### Error: "Can't connect to MySQL server"

Espera unos segundos a que MySQL termine de inicializarse. Puedes verificar el estado con:

```bash
docker-compose logs db
```

Busca el mensaje "ready for connections" en los logs.

### Error: "Access denied for user"

Verifica que las credenciales en `.env` coincidan con las configuradas en MySQL.

### Resetear la base de datos completamente

```bash
docker-compose down -v
docker-compose up -d
```

Esto eliminará todos los datos y creará una base de datos limpia.

## Tecnologías Utilizadas

- Django 5.1.7
- Django REST Framework 3.15.2
- MySQL 8.0
- Docker & Docker Compose
- Python 3.11

## Licencia

Este proyecto es para uso educativo/personal.

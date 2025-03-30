# FriendlyBet - Backend API

A Django REST API for a sports betting and prediction platform that allows users to create rooms, join competitions, and make predictions on sports matches.

## 🔍 Project Overview

FriendlyBet is a full-stack application consisting of:
- This Django backend (REST API)
- A separate [React frontend](https://github.com/nicoclo205/web-nico-project-fe) for the user interface

The backend handles data persistence, business logic, authentication, and provides API endpoints for the frontend to consume.

## 🛠️ Technology Stack

- **Python 3.12+**: Core programming language
- **Django**: Web framework
- **Django REST Framework**: For building the REST API
- **MySQL**: Database engine
- **Token Authentication**: For secure API access

## 📋 Features

- User registration and authentication
- Creating and joining betting rooms
- Sports match data management
- Making predictions on match outcomes
- Scoring system based on prediction accuracy
- Rankings and leaderboards
- In-app messaging system

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- MySQL 8.0+
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nicoclo205/bet_project.git
   cd bet_project
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # On Windows
   # OR
   source .venv/bin/activate      # On Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your local database:
   ```sql
   CREATE DATABASE bet_db;
   CREATE USER 'nico'@'localhost' IDENTIFIED BY 'C0r4z0n#25';
   GRANT ALL PRIVILEGES ON bet_db.* TO 'nico'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. Create an `.env.local` file in the project root with the following content:
   ```
   DJANGO_ENV=local
   DEBUG=True
   SECRET_KEY=django-insecure-7byai@vg_-xt#$gi^nlzfp-ccj5*#@zwm%c3w9i8ld4t9!o6)n
   DB_NAME=bet_db
   DB_USER=nico
   DB_PASSWORD=C0r4z0n#25
   DB_HOST=localhost
   DB_PORT=3306
   ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:5173
   ```

6. Run migrations:
   ```bash
   python manage.py migrate
   ```

7. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

8. Start the development server:
   ```bash
   python manage.py runserver
   ```

The API will be available at http://127.0.0.1:8000/

## 📁 Project Structure

- `bet_project/`: Django project settings and configuration
- `bets/`: Main Django app with models, views, etc.
- `bets/models.py`: Database schema definitions
- `bets/views.py`: API endpoint handlers
- `bets/serializers.py`: Data serialization for API
- `bets/urls.py`: API routing configuration

## 🔌 API Endpoints

- `/admin/`: Django admin interface
- `/api/`: API root
- `/api-auth/`: DRF authentication views
- `/login/`: Login endpoint
- `/logout/`: Logout endpoint
- `/api-token-auth/`: Token authentication

## 🗄️ Database Configuration

The project supports multiple database configurations through environment variables:

- **Local Development**: Using local MySQL instance
- **Railway External**: Connecting to Railway DB from local machine
- **Railway**: Full deployment on Railway platform

Select the environment by setting the `DJANGO_ENV` environment variable to `local`, `railway_external`, or `railway`.

## 🚢 Deployment

The project is configured for deployment on Railway platform:

1. Push code to the repository
2. Railway will automatically detect the Django project
3. Set the required environment variables in Railway dashboard
4. The deployment will use `railway.json` and `Procfile` for configuration

## 🔄 Development Workflow

1. Create a feature branch from `master`
2. Make your changes
3. Test changes locally
4. Create a pull request to merge into `master`
5. After review, merge the pull request

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 👥 Authors

- nicoclo205 - Initial work and maintenance
- mikla01 - Collaborator

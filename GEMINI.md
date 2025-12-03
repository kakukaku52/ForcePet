# GEMINI.md

## Project Overview

This is a Django-based Salesforce developer tool that replicates the functionality of the original PHP Workbench. This application provides a comprehensive interface for working with Salesforce APIs including SOQL queries, data manipulation, metadata operations, Apex execution, and more.

The project uses Django and Django REST Framework for the backend, with Celery for asynchronous tasks. It integrates with Salesforce using the `simple-salesforce` library.

## Building and Running

### Method 1: Docker Compose (Recommended)

1.  **Configure environment variables**:
    ```bash
    cp .env.example .env
    # Edit .env with your Salesforce Connected App credentials
    ```

2.  **Start the application**:
    ```bash
    docker-compose up -d
    ```

3.  **Access the application**:
    *   Web interface: http://localhost:8000
    *   Admin interface: http://localhost:8000/admin (admin/admin123)

### Method 2: Local Development

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up the database**:
    ```bash
    python manage.py migrate
    ```

3.  **Create a superuser**:
    ```bash
    python manage.py createsuperuser
    ```

4.  **Start the development server**:
    ```bash
    python manage.py runserver
    ```

5.  **Start Celery worker** (in another terminal):
    ```bash
    celery -A workbench_project worker -l info
    ```

6.  **Start Celery beat** (in another terminal):
    ```bash
    celery -A workbench_project beat -l info
    ```

## Development Conventions

*   **Token Encryption**: All Salesforce tokens are encrypted before storage.
*   **Session Management**: Secure session handling with automatic expiration.
*   **CSRF Protection**: Cross-site request forgery protection is enabled.
*   **Input Validation**: The project emphasizes comprehensive input validation and sanitization.
*   **API Rate Limiting**: The application is designed to respect Salesforce API limits.
*   **Caching**: Redis-based caching is used for improved performance.
*   **Async Processing**: Celery is used for background tasks.
*   **Logging**: Logs are written to `/app/logs/workbench.log`.
*   **Code Style**: The project follows standard Django and Python coding conventions.
*   **Testing**: The `tests.py` files in each app suggest that the project has a testing framework in place, likely using Django's built-in test runner.
*   **Contributing**: The `docs/README.md` outlines a standard fork-and-pull-request workflow for contributions.
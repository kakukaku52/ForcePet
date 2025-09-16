# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based Salesforce developer tool that replicates the functionality of Salesforce Workbench. It provides a comprehensive interface for working with Salesforce APIs including SOQL queries, data manipulation, metadata operations, Apex execution, and more.

## Development Commands

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Database setup
python manage.py migrate

# Create superuser (first time only)
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run Celery worker (in separate terminal)
celery -A workbench_project worker -l info

# Run Celery beat (in separate terminal)
celery -A workbench_project beat -l info
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Testing and Quality

```bash
# Run Django tests
python manage.py test

# Run specific app tests
python manage.py test authentication
python manage.py test query

# Check for migrations
python manage.py makemigrations --check
```

## Architecture

### Project Structure

- **workbench_project/**: Main Django project configuration
  - `settings.py`: Django settings with environment variable support
  - `urls.py`: Main URL configuration routing to app-specific URLs
  - `celery.py`: Celery configuration for async tasks

### Core Applications

- **authentication/**: Salesforce OAuth and session management
  - `salesforce_client.py`: Unified API client for all Salesforce operations
  - `middleware.py`: Session management middleware
  - `models.py`: SalesforceConnection model for storing auth tokens

- **query/**: SOQL/SOSL query functionality
  - Handles query execution, history tracking, and result export

- **data/**: CRUD operations for Salesforce records
  - Insert, Update, Upsert, Delete, Undelete operations

- **metadata/**: Salesforce metadata operations
  - Object description, metadata retrieval and deployment

- **apex/**: Apex code execution
  - Anonymous Apex execution, test running, debug logs

- **bulk/**: Bulk API operations
  - Large dataset handling with async job management

- **rest_explorer/**: Interactive REST API explorer
  - Visual interface for testing Salesforce REST endpoints

- **streaming/**: Streaming API implementation
  - Push topics, platform events, generic streaming

### Key Design Patterns

1. **Unified Client Pattern**: All Salesforce API interactions go through `SalesforceClient` class in `authentication/salesforce_client.py`

2. **Session Management**: Custom middleware (`SalesforceSessionMiddleware`) handles Salesforce session state

3. **Async Processing**: Celery is used for long-running operations like bulk data processing

4. **Environment-based Configuration**: Uses `.env` file for configuration with sensible defaults

## Environment Variables

Required for production:
- `SECRET_KEY`: Django secret key
- `SALESFORCE_CONSUMER_KEY`: Connected App consumer key
- `SALESFORCE_CONSUMER_SECRET`: Connected App consumer secret
- `SALESFORCE_REDIRECT_URI`: OAuth callback URL

Optional:
- `DEBUG`: Set to False in production
- `DATABASE_URL`: PostgreSQL connection string (uses SQLite if not set)
- `REDIS_URL`: Redis connection for caching/Celery
- `SALESFORCE_API_VERSION`: API version (default: 62.0)

## Salesforce Integration

The project uses multiple Salesforce APIs:
- **REST API**: Via `simple-salesforce` library
- **SOAP API**: Via `zeep` library for certain operations
- **Bulk API**: For large data operations
- **Streaming API**: For real-time data updates

Authentication supports:
- OAuth 2.0 Web Server Flow
- Username/Password (for development)
- Session token management with encryption

## Database Models

Key models across apps:
- `SalesforceConnection`: Stores encrypted Salesforce tokens
- `QueryHistory`: Tracks all executed queries
- `BulkJob`: Manages bulk operation status
- `SavedQuery`: User's saved SOQL queries

## Static Files and Templates

- Templates use Django's template system with Bootstrap styling
- Static files served via WhiteNoise in production
- Base template: `templates/base.html`
- App-specific templates in `[app]/templates/[app]/`
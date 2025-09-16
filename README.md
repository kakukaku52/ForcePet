# Django Workbench

A Django-based Salesforce developer tool that replicates the functionality of the original PHP Workbench. This application provides a comprehensive interface for working with Salesforce APIs including SOQL queries, data manipulation, metadata operations, Apex execution, and more.

## Features

### 🔐 Authentication
- **OAuth 2.0 Integration**: Secure authentication with Salesforce using OAuth 2.0
- **Username/Password Support**: Traditional login for development environments
- **Multi-Environment**: Support for Production, Sandbox, and Custom domains
- **Session Management**: Secure token encryption and automatic refresh

### 🔍 Query & Search
- **SOQL Query Interface**: Full-featured SOQL query editor with syntax highlighting
- **SOSL Search**: Search across multiple objects with SOSL
- **Query History**: Track all executed queries with performance metrics
- **Saved Queries**: Save and organize frequently used queries
- **Export Results**: Export query results to CSV or JSON formats
- **Pagination**: Handle large result sets efficiently

### 📊 Data Operations
- **Insert**: Add new records to Salesforce objects
- **Update**: Modify existing records
- **Upsert**: Insert or update based on external ID
- **Delete**: Remove records from Salesforce
- **Undelete**: Restore deleted records from the recycle bin

### ⚙️ Metadata Management
- **Describe Objects**: Get detailed information about Salesforce objects
- **List Metadata**: Browse available metadata components
- **Retrieve**: Download metadata from your org
- **Deploy**: Deploy metadata changes to your org

### 💻 Apex Development
- **Execute Anonymous**: Run Apex code snippets
- **Test Execution**: Run Apex tests and view results
- **Debug Logs**: Access debug log information

### 📦 Bulk Operations
- **Bulk API Integration**: Handle large data sets efficiently
- **Async Job Management**: Monitor bulk job progress
- **CSV Processing**: Upload and process CSV files
- **Job History**: Track all bulk operations

### 🌐 REST Explorer
- **Interactive API Explorer**: Test REST API endpoints
- **Request Builder**: Visual interface for building API requests
- **Response Viewer**: Formatted JSON response display
- **API Documentation**: Built-in reference for common endpoints

### 📡 Streaming API
- **Push Topics**: Subscribe to data changes
- **Platform Events**: Monitor platform events
- **Generic Streaming**: Connect to custom streaming channels

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 12+ (or SQLite for development)
- Redis 6+
- Docker & Docker Compose (for containerized deployment)

### Method 1: Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd django-workbench
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Salesforce Connected App credentials
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Web interface: http://localhost:8000
   - Admin interface: http://localhost:8000/admin (admin/admin123)

### Method 2: Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up the database**:
   ```bash
   python manage.py migrate
   ```

3. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```

4. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

5. **Start Celery worker** (in another terminal):
   ```bash
   celery -A workbench_project worker -l info
   ```

6. **Start Celery beat** (in another terminal):
   ```bash
   celery -A workbench_project beat -l info
   ```

## Configuration

### Salesforce Connected App Setup

1. **Create a Connected App** in Salesforce:
   - Go to Setup > App Manager > New Connected App
   - Enable OAuth Settings
   - Set Callback URL: `http://localhost:8000/auth/callback/`
   - Select scopes: `Full access (full)`, `Refresh token (refresh_token)`

2. **Update environment variables**:
   ```bash
   SALESFORCE_CONSUMER_KEY=your_consumer_key
   SALESFORCE_CONSUMER_SECRET=your_consumer_secret
   SALESFORCE_REDIRECT_URI=http://localhost:8000/auth/callback/
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Enable debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed hostnames | `localhost,127.0.0.1` |
| `DATABASE_URL` | Database connection string | SQLite (development) |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SALESFORCE_API_VERSION` | Salesforce API version | `62.0` |
| `SALESFORCE_CONSUMER_KEY` | Connected App consumer key | Required |
| `SALESFORCE_CONSUMER_SECRET` | Connected App consumer secret | Required |
| `SALESFORCE_REDIRECT_URI` | OAuth redirect URI | Required |

## Usage

### Basic Workflow

1. **Login**: Use OAuth or username/password to connect to Salesforce
2. **Query Data**: Use the SOQL interface to query your data
3. **Manipulate Data**: Insert, update, or delete records
4. **Explore Metadata**: Describe objects and browse metadata
5. **Execute Apex**: Run anonymous Apex code or tests
6. **Bulk Operations**: Handle large datasets efficiently

### Example SOQL Queries

```sql
-- Basic query
SELECT Id, Name, Email FROM Contact LIMIT 10

-- Query with conditions
SELECT Id, Name, Industry FROM Account 
WHERE Industry = 'Technology' 
ORDER BY Name ASC

-- Query with relationships
SELECT Id, Name, Account.Name, Account.Industry 
FROM Contact 
WHERE Account.Industry != null
```

### Example SOSL Searches

```sql
-- Search across multiple objects
FIND {john} IN ALL FIELDS 
RETURNING Account(Id, Name), Contact(Id, Name, Email)

-- Search in specific fields
FIND {smith} IN NAME FIELDS 
RETURNING Contact(Id, Name, Email, Phone)
```

## Architecture

### Project Structure
```
django-workbench/
├── workbench_project/       # Django project settings
├── authentication/          # Salesforce authentication
├── query/                  # SOQL/SOSL functionality
├── data/                   # Data manipulation operations
├── metadata/               # Metadata operations
├── apex/                   # Apex execution
├── bulk/                   # Bulk API operations
├── rest_explorer/          # REST API explorer
├── streaming/              # Streaming API
├── templates/              # HTML templates
├── static/                 # Static files (CSS, JS)
└── requirements.txt        # Python dependencies
```

### Key Components

- **SalesforceClient**: Unified API client for all Salesforce operations
- **Authentication Middleware**: Manages Salesforce sessions
- **Async Jobs**: Celery tasks for long-running operations
- **Query History**: Tracks all API operations
- **Settings Management**: User-specific configuration

## API Endpoints

### Authentication
- `POST /auth/login/` - Login form
- `GET /auth/callback/` - OAuth callback
- `POST /auth/logout/` - Logout
- `GET /auth/session/` - Session information

### Query
- `GET|POST /query/` - SOQL query interface
- `GET|POST /query/search/` - SOSL search interface
- `GET /query/export/<id>/` - Export results
- `GET /query/history/` - Query history

### Data Operations
- `GET|POST /data/insert/` - Insert records
- `GET|POST /data/update/` - Update records
- `GET|POST /data/delete/` - Delete records
- `GET|POST /data/upsert/` - Upsert records

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security Considerations

- **Token Encryption**: All Salesforce tokens are encrypted before storage
- **Session Management**: Secure session handling with automatic expiration
- **CSRF Protection**: Cross-site request forgery protection
- **Input Validation**: Comprehensive input validation and sanitization
- **API Rate Limiting**: Respect Salesforce API limits

## Performance

- **Caching**: Redis-based caching for improved performance
- **Async Processing**: Celery for background tasks
- **Connection Pooling**: Efficient database connections
- **Static Files**: Optimized static file serving

## Troubleshooting

### Common Issues

1. **OAuth Login Fails**:
   - Verify Connected App configuration
   - Check callback URL matches exactly
   - Ensure proper OAuth scopes are selected

2. **Database Connection Errors**:
   - Verify PostgreSQL is running
   - Check database credentials in environment variables

3. **Celery Tasks Not Processing**:
   - Ensure Redis is running
   - Check Celery worker logs
   - Verify broker URL configuration

### Logging

Logs are written to `/app/logs/workbench.log` and include:
- API request/response details
- Authentication events
- Error traces
- Performance metrics

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original PHP Workbench project
- Salesforce Developer Community
- Django and Python communities

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review existing issues on GitHub
3. Create a new issue with detailed information
4. Join our community discussions
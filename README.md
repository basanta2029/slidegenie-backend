# SlideGenie Backend

AI-powered academic presentation generator backend built with FastAPI, PostgreSQL, and clean architecture principles.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Poetry (for dependency management)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd slidegenie-backend
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   make dev-install
   ```

4. **Start services**
   ```bash
   make docker-up
   ```

5. **Run migrations**
   ```bash
   make migrate
   ```

6. **Start the development server**
   ```bash
   make run
   ```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/api/v1/docs`

## 🏗️ Architecture

This project follows clean architecture principles:

```
app/
├── api/              # REST API endpoints
│   └── v1/
│       ├── endpoints/
│       └── dependencies/
├── core/             # Core application code
│   ├── config.py     # Configuration management
│   ├── security.py   # Security utilities
│   └── logging.py    # Logging configuration
├── domain/           # Business logic
│   ├── entities/     # Domain entities
│   ├── interfaces/   # Repository interfaces
│   └── schemas/      # Pydantic schemas
├── infrastructure/   # External services
│   ├── database/     # Database models and config
│   ├── cache/        # Redis cache
│   ├── storage/      # MinIO/S3 storage
│   └── external/     # External API clients
├── services/         # Business logic services
└── repositories/     # Data access layer
```

## 🛠️ Development

### Available Commands

```bash
# Development
make run            # Run development server
make format         # Format code with black and isort
make lint           # Run linters
make type-check     # Run type checking with mypy
make test           # Run tests
make test-coverage  # Run tests with coverage report

# Docker
make docker-up      # Start all services
make docker-down    # Stop all services
make docker-logs    # View logs
make docker-build   # Build images

# Database
make migrate        # Run migrations
make migrate-create # Create new migration
make db-shell       # Access PostgreSQL shell
make redis-cli      # Access Redis CLI

# Utilities
make clean          # Clean cache files
make setup          # Complete setup
make check          # Run all checks
```

### Code Quality

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **pytest** for testing
- **pre-commit** hooks for ensuring code quality

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

Run manually:
```bash
pre-commit run --all-files
```

## 🗄️ Database

### PostgreSQL with pgvector

The project uses PostgreSQL 16 with pgvector extension for AI embeddings.

Create a migration:
```bash
make migrate-create
```

### Models

- **User**: User accounts and authentication
- **Presentation**: Generated presentations
- **Slide**: Individual slides within presentations
- **Template**: Presentation templates
- **Reference**: Citations and references
- **Collaboration**: Shared presentation access
- **GenerationJob**: Background job tracking
- **Export**: Export history
- **APIKey**: API access keys

## 🔒 Security

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- API rate limiting
- Request validation
- CORS configuration
- SQL injection prevention

## 🧪 Testing

Run tests:
```bash
make test
```

Run with coverage:
```bash
make test-coverage
```

Test structure:
```
tests/
├── unit/        # Unit tests
├── integration/ # Integration tests
└── e2e/         # End-to-end tests
```

## 📊 Monitoring

- Structured logging with structlog
- Sentry integration for error tracking
- Health check endpoints
- Performance metrics
- Request tracing

## 🚀 Deployment

### Docker

Build production image:
```bash
docker build -t slidegenie-backend:latest .
```

### Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `SECRET_KEY`: JWT signing key (required)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ANTHROPIC_API_KEY`: Claude API key
- `OPENAI_API_KEY`: OpenAI API key (fallback)

## 📝 API Documentation

- Swagger UI: `/api/v1/docs`
- ReDoc: `/api/v1/redoc`
- OpenAPI schema: `/api/v1/openapi.json`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

[MIT License](LICENSE)
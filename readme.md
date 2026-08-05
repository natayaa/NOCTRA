# Workshop Management API

Workshop Management System API for managing customer inquiries, projects, payments, inventory, and price lists.

## Features

- **Inquiry Management**: Create, track, and convert customer inquiries
- **Project Management**: Manage projects with tasks, labor, and expenses
- **Payment System**: Handle deposits, invoices, and payments
- **Inventory Management**: Track stock, materials, and suppliers
- **Price List**: Manage services, materials, and pricing
- **Authentication**: JWT-based authentication (coming soon)

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 (async)
- PostgreSQL
- Redis (caching)
- Celery (background tasks)
- Docker & Docker Compose

## Quick Start

### Development

```bash
# Clone repository
git clone https://github.com/your-repo/workshop-backend.git
cd workshop-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Run migrations
alembic upgrade head

# Start application
uvicorn main:app --reload
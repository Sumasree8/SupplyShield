# SupplyShield AI — Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- Git
- (Production) AWS CLI configured with ECS permissions
- (Production) Domain name with DNS control

---

## Local Development Setup

### 1. Clone and configure environment

```bash
git clone https://github.com/your-org/supplychield.git
cd supplychield

cp .env.example .env
```

Edit `.env` and set at minimum:
```bash
SECRET_KEY=$(openssl rand -hex 32)  # Generate a real key
POSTGRES_PASSWORD=your_strong_password
NEO4J_PASSWORD=your_neo4j_password
```

### 2. Start all services

```bash
docker compose up -d
```

Services started:
| Service    | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000      |
| Backend   | http://localhost:8000      |
| API Docs  | http://localhost:8000/api/docs |
| Neo4j     | http://localhost:7474      |
| Grafana   | http://localhost:3001      |
| Prometheus| http://localhost:9090      |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Create first admin account

Register via the UI at http://localhost:3000/register, or via API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "password": "SecurePassword123!",
    "full_name": "Platform Admin",
    "organization_name": "Your Company",
    "industry": "Manufacturing"
  }'
```

### 4b. (Optional) Seed demo data

To explore the platform with a realistic sample supply chain instead of starting empty:

```bash
docker compose exec backend python scripts/seed_demo.py
```

This creates a 4-tier automotive supply chain (Denso, Bosch, Magna, Continental at Tier 1,
down to raw material suppliers at Tier 3) with a deliberately flagged sole-source dependency,
plus four demo user logins — one per role. All records are labeled `[DEMO]`. Intended for
development and demonstration only; do not run against a production database.

### 5. Configure external API keys (optional but recommended)

Add to `.env`:
```bash
OPENWEATHER_API_KEY=your_key    # https://openweathermap.org/api
NOAA_API_KEY=your_key          # https://www.weather.gov/documentation/services-web-api
NEWS_API_KEY=your_key          # https://newsapi.org
SLACK_WEBHOOK_URL=https://...  # For alert notifications
```

Restart services to pick up new keys:
```bash
docker compose restart celery_worker celery_beat
```

---

## Production Deployment (AWS ECS)

### 1. Push images to ECR

```bash
# Authenticate
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t supplychield-backend ./backend
docker tag supplychield-backend:latest $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/supplychield-backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/supplychield-backend:latest

docker build -t supplychield-frontend ./frontend
docker tag supplychield-frontend:latest $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/supplychield-frontend:latest
docker push $AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/supplychield-frontend:latest
```

### 2. Infrastructure requirements (AWS)

- **ECS Cluster** (Fargate recommended)
- **RDS PostgreSQL 16** (Multi-AZ for production)
- **ElastiCache Redis** (cluster mode optional)
- **Neo4j AuraDB** or self-hosted on EC2
- **Application Load Balancer** with SSL termination
- **ACM Certificate** for HTTPS
- **Secrets Manager** for all secret values
- **VPC** with private subnets for databases

### 3. Environment variables in ECS

Store all secrets in AWS Secrets Manager and reference them in ECS task definitions:

```json
{
  "secrets": [
    {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "POSTGRES_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."},
    {"name": "NEO4J_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}
  ]
}
```

**Never** pass secrets as plaintext environment variables in task definitions.

### 4. Run migrations on deploy

Add a migration task to your ECS deployment:

```bash
aws ecs run-task \
  --cluster supplychield-cluster \
  --task-definition supplychield-migrate \
  --overrides '{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}'
```

### 5. CI/CD via GitHub Actions

See `.github/workflows/ci.yml`. Required secrets in GitHub:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`  
- `AWS_REGION`
- `SLACK_WEBHOOK_URL` (optional, for deploy notifications)

---

## Health Checks

```bash
# Backend health
curl http://localhost:8000/api/v1/health

# Expected response
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "graph_database": "ok"
  },
  "version": "1.0.0"
}
```

---

## Monitoring

- **Grafana**: http://localhost:3001 (default: admin/admin — change in production)
- **Prometheus**: http://localhost:9090
- **Backend metrics**: http://localhost:8000/metrics (Prometheus format)

Key metrics to watch:
- `http_requests_total` — request volume by status code
- `http_request_duration_seconds` — latency percentiles
- PostgreSQL connection pool usage
- Celery task queue depth (risk ingestion jobs)

---

## Backup Strategy

### PostgreSQL
```bash
# Daily backup
docker compose exec postgres pg_dump -U ss_user supplychield > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T postgres psql -U ss_user supplychield < backup_20250101.sql
```

### Neo4j
Use Neo4j's built-in backup tool or AuraDB's automated backups.

---

## Troubleshooting

**Backend won't start:**
```bash
docker compose logs backend
# Check for missing SECRET_KEY or DATABASE_URL
```

**Database connection refused:**
```bash
docker compose ps postgres  # Must be "healthy"
docker compose logs postgres
```

**Neo4j not connecting (non-fatal):**
The backend falls back to NetworkX automatically. Check logs:
```bash
docker compose logs backend | grep graph_database
```

**Celery not ingesting events:**
```bash
docker compose logs celery_worker
# Check OPENWEATHER_API_KEY / NOAA_API_KEY are set
```

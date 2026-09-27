# Fleet Telemetry Platform

## Architecture

```text
React/Vite
   |
   v
FastAPI -> PostgreSQL

Simulator -> MQTT broker (broker.emqx.io)
                         |
                         v
                      FastAPI
                         |
              +----------+----------+
              v                     v
         PostgreSQL             Redis Pub/Sub
                                      |
                                      v
                                  WebSocket
                                      |
                                      v
                                    React
```

PostgreSQL is the durable source of telemetry. Redis is the real-time fan-out layer.
The backend is the authentication, tenancy, trip-state, and route-deviation authority.

## Local Development

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `VITE_API_BASE_URL` and defaults to `http://localhost:8000` locally.

## Production Deployment

The repository includes [render.yaml](render.yaml) for a Render deployment consisting of:

- FastAPI web service
- Render PostgreSQL
- Render Redis service (Render's managed Redis/Key Value equivalent)
- React/Vite static site with SPA fallback

The backend starts with:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render runs `alembic upgrade head` as the pre-deploy command. Review the Blueprint resource settings in the Render dashboard before creating production resources.

After the first organization exists, provision the required users with environment
variables supplied only in the deployment shell or secret manager:

```powershell
$env:SUPER_ADMIN_EMAIL='<provided separately>'
$env:SUPER_ADMIN_PASSWORD='<provided separately>'
$env:REGULAR_USER_EMAIL='<provided separately>'
$env:REGULAR_USER_PASSWORD='<provided separately>'
$env:REGULAR_USER_ORGANIZATION_NAME='<organization name>'
cd backend
..\.venv\Scripts\python.exe -m app.scripts.seed_admin
```

Use `REGULAR_USER_ORGANIZATION_ID` instead when an organization already exists.
The provisioning command is idempotent for existing email addresses, creates the
organization only when a name is supplied and missing, and never prints passwords.
There is no public signup endpoint.

## Environment Variables

Variable names only; values must be supplied through the deployment environment:

```text
DATABASE_URL
DATABASE_HOST
DATABASE_PORT
DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD
JWT_SECRET_KEY
JWT_ALGORITHM
JWT_EXPIRE_MINUTES
REDIS_URL
REDIS_HOST
REDIS_PORT
REDIS_DB
REDIS_PASSWORD
REDIS_CHANNEL_PREFIX
CORS_ALLOWED_ORIGINS
MQTT_BROKER_HOST
MQTT_BROKER_PORT
MQTT_USERNAME
MQTT_PASSWORD
MQTT_TOPIC_PREFIX
VEHICLE_OFFLINE_THRESHOLD_SECONDS
VEHICLE_OFFLINE_CHECK_INTERVAL_SECONDS
ROUTE_DEVIATION_THRESHOLD_METERS
EMAIL_ENABLED
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM_EMAIL
SMTP_USE_TLS
ROUTE_ALERT_RECIPIENT_EMAIL
```

Local `.env` files are ignored and must never be committed.

## Database Migration

```powershell
cd backend
alembic upgrade head
```

The current migration head is `171e4dfe077f`.

## Simulator

The simulator is a publisher only. It is not required for the public frontend deployment and must not be started as a second MQTT subscriber.

```powershell
cd simulator
..\backend\.venv\Scripts\python.exe simulator.py
```

Update `simulator/config.json` with valid active trip IDs before publishing. The current demonstration mapping is vehicle 1/trip 2, vehicle 2/trip 3, and vehicle 3/trip 4.

## Planned Routes and Alerts

Upload a KML `LineString` to an active or not-completed trip through the dashboard or:

```text
POST /trips/{trip_id}/route
```

The backend normalizes route coordinates, compares validated telemetry to the planned polyline, and sends one SMTP alert on the first deviation incident. Repeated off-route points are suppressed until the vehicle returns within the configured threshold.

Set `EMAIL_ENABLED=true` and provide the SMTP variables for real delivery. Email failure never rolls back telemetry.

## Health and API Documentation

- Health: `/health`
- Database health: `/health/database`
- API docs: `/docs`

## Submission Checklist

- [ ] Deployed backend URL
- [ ] Super Admin credentials supplied separately
- [ ] Regular User credentials supplied separately
- [ ] Live dashboard verified
- [ ] WebSocket verified
- [ ] Historical trip verified
- [ ] CSV export verified
- [ ] KML route upload verified
- [ ] Route deviation verified
- [ ] SMTP alert verified if configured

# CarePoint Pharmacy Test Scheduling API

A small, deployable test API for connecting Rafiki AI's **Custom scheduling** service.

## What it supports

- `GET /availability?appointment_date=YYYY-MM-DD&duration_minutes=30`
- `POST /appointments`
- `GET /appointments/{booking_id}`
- `GET /appointments` (test/admin listing)
- `DELETE /appointments/{booking_id}`
- `GET /health`

## Test clinic hours

- Monday-Friday: 08:00-18:00
- Saturday: 09:00-15:00
- Sunday: closed
- Weekday lunch break: 13:00-14:00
- Default appointment length: 30 minutes
- Time zone: Africa/Nairobi

## Deploy on Render

1. Create a GitHub repository and upload these files.
2. In Render, choose **New + → Web Service** and connect the repository.
3. Runtime: Python.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy. Render will provide a public HTTPS URL, for example `https://your-service.onrender.com`.
7. Open `https://YOUR-URL/health`; it should return `{"status":"ok",...}`.
8. Open `https://YOUR-URL/docs` to inspect and manually test the API.

## Rafiki Custom scheduling fields

**Do not use the example host below.** Use the real HTTPS URL Render gives you after deployment.

Base URL:
`https://YOUR-RENDER-SERVICE.onrender.com`

Operations (initial connector configuration):
```json
{
  "lookup_availability": {
    "request": {
      "method": "GET",
      "path": "/availability"
    }
  },
  "book_appointment": {
    "request": {
      "method": "POST",
      "path": "/appointments"
    }
  }
}
```

Important: Rafiki's Custom scheduling connector may require specific parameter names/body mappings for the `lookup_availability` and `book_appointment` operations. The two-operation JSON above declares the endpoint paths, but does not guarantee that Rafiki will send the request fields this API expects. After deployment, use the API documentation at `/docs` and Rafiki's test result/error to align field mappings.

## Manual API test examples

Availability:
```bash
curl "https://YOUR-URL/availability?appointment_date=2026-11-20&duration_minutes=30"
```

Book:
```bash
curl -X POST "https://YOUR-URL/appointments" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Jane Wanjiku",
    "customer_phone": "+254712345678",
    "appointment_date": "2026-11-20",
    "appointment_time": "10:00",
    "reason": "Pharmacy consultation",
    "duration_minutes": 30
  }'
```

## Test-only limitations

- Bookings are stored in memory and may be lost when the service restarts or sleeps.
- This is not production-ready and has no authentication, persistent database, staff/resource calendars, or patient-data protections.
- Use fictional customer data only. Do not put real patient information into this test API.
- Add authentication and persistent storage before any real customer use.

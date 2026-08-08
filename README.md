# Multi-Rate Pricing Calculator API

## Run the API

1. Install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Start the server:

```bash
uvicorn backend.app.main:app --reload
```

3. Open the Swagger UI:

- `http://127.0.0.1:8000/docs`

## API usage

### Signup

- `POST /signup`
- Query parameters: `email`, `password`
- Creates a user account.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/signup?email=test@example.com&password=secret123"
```

### Login

- `POST /token`
- Form fields: `username`, `password`
- Returns `access_token`.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/token" -F "username=test@example.com" -F "password=secret123"
```

### Authenticated requests

- Include header: `Authorization: Bearer <access_token>`

Example header:

```bash
-H "Authorization: Bearer <access_token>"
```

### Create document

- `POST /documents`
- Query parameters: `title`, `customer` (optional), `issue_date` (optional)
- Requires auth.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/documents?title=Invoice&customer=Acme&issue_date=2026-08-01" \
  -H "Authorization: Bearer <access_token>"
```

### Get document

- `GET /documents/{doc_id}`
- Returns document lines and computed totals.
- Requires auth.

Example:

```bash
curl "http://127.0.0.1:8000/documents/1" \
  -H "Authorization: Bearer <access_token>"
```

### Add line item

- `POST /documents/{doc_id}/lines`
- Query parameters:
  - `description`
  - `quantity` (>= 1)
  - `unit_price` (>= 0)
  - `discount_amount` OR `discount_percent` (not both)
  - `tax_percent` (optional)
- Requires auth.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/documents/1/lines?description=Widget+A&quantity=2&unit_price=100.00&discount_percent=10&tax_percent=5" \
  -H "Authorization: Bearer <access_token>"
```

### Finalize document

- `POST /documents/{doc_id}/finalize`
- Once finalized, the document cannot be modified.
- Requires auth.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/documents/1/finalize" \
  -H "Authorization: Bearer <access_token>"
```

### Report

- `GET /report`
- Query parameters: `start_date`, `end_date`
- Returns document counts and totals for the date range.
- Requires auth.

Example:

```bash
curl "http://127.0.0.1:8000/report?start_date=2026-08-01&end_date=2026-08-31" \
  -H "Authorization: Bearer <access_token>"
```

## Validation rules

- `quantity` must be `>= 1`
- `unit_price` must be `>= 0`
- `discount_amount` and `discount_percent` cannot both be provided
- Finalized documents reject line edits
- Use the Swagger UI at `/docs` to enter values and validate format interactively

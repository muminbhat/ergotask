# Smart Todo API usage notes

## Auth
- Obtain token: POST `/api/auth/token/` with `{ "username": "...", "password": "..." }`
- Use header: `Authorization: Bearer <access>`
- Refresh: POST `/api/auth/token/refresh/` with `{ "refresh": "..." }`

## Tasks
- List: GET `/api/v1/tasks/?ordering=-priority_score`
- Create: POST `/api/v1/tasks/`

Example:
```json
{ "title": "Prepare Q3 report", "description": "Collect metrics" }
```

- AI suggestions: POST `/api/v1/tasks/{id}/ai-suggestions/`

## Contexts
- Add: POST `/api/v1/contexts/`

Example:
```json
{ "content": "Boss: send the Q3 report by Wednesday", "source_type": "email" }
```

- List: GET `/api/v1/contexts/?source_type=email`

## Categories
- List: GET `/api/v1/categories/`

## Docs
- Swagger: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI JSON: `/api/schema/`


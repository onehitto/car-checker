# Car Checker — design documentation

Design documentation of the Car Checker backend API, database and web app. The
backend sections follow the order requested in the specification.

| #  | Section                                         | Document                                                   |
|----|-------------------------------------------------|------------------------------------------------------------|
| 1  | Recommended backend technology stack            | [01-architecture.md](01-architecture.md#1-recommended-backend-technology-stack) |
| 2  | Backend project folder structure                | [01-architecture.md](01-architecture.md#2-backend-project-folder-structure) |
| 3  | System architecture explanation                 | [01-architecture.md](01-architecture.md#3-system-architecture) |
| 4  | Complete database ER model                      | [02-database.md](02-database.md#4-er-model)                |
| 5  | Database table definitions                      | [02-database.md](02-database.md#5-table-definitions)       |
| 6  | SQL schema / ORM models                         | [02-database.md](02-database.md#6-sql-schema--orm-models)  |
| 7  | Relationships between entities                  | [02-database.md](02-database.md#7-relationships-between-entities) |
| 8  | Authentication architecture                     | [03-security.md](03-security.md#8-authentication-architecture) |
| 9  | Authorization architecture                      | [03-security.md](03-security.md#9-authorization-architecture) |
| 10 | Complete API endpoint list                      | [04-api.md](04-api.md#10-endpoint-list)                    |
| 11 | Request and response DTOs                       | [04-api.md](04-api.md#11-request-and-response-dtos-main-schemas) |
| 12 | Validation rules                                | [04-api.md](04-api.md#12-validation-rules)                 |
| 13 | Maintenance calculation logic                   | [05-domain-logic.md](05-domain-logic.md#13-maintenance-calculation-logic) |
| 14 | Alert generation logic                          | [05-domain-logic.md](05-domain-logic.md#14-alert-generation-logic) |
| 15 | Document expiration logic                       | [05-domain-logic.md](05-domain-logic.md#15-document-expiration-logic) |
| 16 | Expense and fuel calculation logic              | [05-domain-logic.md](05-domain-logic.md#16-expense-and-fuel-calculation-logic) |
| 17 | File upload architecture                        | [06-platform.md](06-platform.md#17-file-upload-architecture) |
| 18 | Background job architecture                     | [06-platform.md](06-platform.md#18-background-job-architecture) |
| 19 | API error handling strategy                     | [04-api.md](04-api.md#19-error-handling-strategy)          |
| 20 | Docker architecture                             | [06-platform.md](06-platform.md#20-docker-architecture)    |
| 21 | Environment variables                           | [06-platform.md](06-platform.md#21-environment-variables)  |
| 22 | Database migrations                             | [02-database.md](02-database.md#22-database-migrations)    |
| 23 | Seed data                                       | [02-database.md](02-database.md#23-seed-data)              |
| 24 | Swagger / OpenAPI setup                         | [06-platform.md](06-platform.md#24-swagger--openapi-setup) |
| 25 | Testing strategy                                | [06-platform.md](06-platform.md#25-testing-strategy)       |
| 26 | Security recommendations                        | [03-security.md](03-security.md#26-security-recommendations-implemented-unless-stated-otherwise) |
| 27 | Example API requests and responses              | [04-api.md](04-api.md#27-example-requests-and-responses)   |
| 28 | Step-by-step implementation plan                | [07-implementation-plan.md](07-implementation-plan.md)     |

Web app (stack, Docker workflow, screens, data refresh, authentication, design
plan, tests): [08-frontend.md](08-frontend.md).

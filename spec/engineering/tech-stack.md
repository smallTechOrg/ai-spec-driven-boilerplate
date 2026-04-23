# Tech Stack — Standup Bot

## Language + Runtime
TypeScript, Bun

## Framework
Hono (lightweight, Bun-native HTTP framework)

## Database
PostgreSQL via Drizzle ORM

## Key Libraries
| Library | Purpose |
|---------|---------|
| hono | HTTP server |
| drizzle-orm | ORM |
| postgres (npm) | PostgreSQL driver |
| @types/bun | Bun types |
| vitest | Testing |

## Dependency Management
Bun + package.json

## Entry Point
`bun run src/index.ts`

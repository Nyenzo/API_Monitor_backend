-- UUID generation helper
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;

-- Outbound HTTP request support for health checks
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- Server-side cron scheduler documentation
-- CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA pg_catalog;

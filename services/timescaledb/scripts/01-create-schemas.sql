-- Create schemas for different bounded contexts
CREATE SCHEMA IF NOT EXISTS tracking;
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant usage to default user (will be set via environment)
-- Note: Actual user permissions should be managed separately

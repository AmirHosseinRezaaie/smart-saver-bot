-- Creates the dedicated integration-test database alongside the
-- development one. Run automatically by the postgres image's
-- docker-entrypoint-initdb.d mechanism; see docker-compose.yml.
CREATE DATABASE shopping_bot_test OWNER ssb;

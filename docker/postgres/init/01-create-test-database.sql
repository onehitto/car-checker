-- Executed once, when the PostgreSQL data volume is initialised.
-- The automated test suite uses its own database so it never touches development data.
CREATE DATABASE car_checker_test OWNER car_checker;

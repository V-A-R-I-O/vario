-- Rasa tracker stores, one database per role pack (ADR-006 §5).
-- Runs only when the postgres volume is first created; on an existing volume
-- each Rasa server creates its database on first start.
CREATE DATABASE rasa_hr;
CREATE DATABASE rasa_it;
CREATE DATABASE rasa_admissions;

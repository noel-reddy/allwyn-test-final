-- Seed a few rows so SELECT shows data
-- 001_insert.sql (correct)
insert into demo.customers (name, joined_date) values ('Alice', current_date);
insert into demo.customers (name, joined_date) values ('Bob', current_date - interval '5 days');
insert into demo.customers (name, joined_date) values ('Charlie', current_date - interval '30 days');
commit;

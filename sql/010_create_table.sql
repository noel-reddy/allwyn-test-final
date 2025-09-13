create table if not exists demo.customers (
  id int identity(1,1),
  name varchar(50),
  joined_date date default current_date
);
commit;
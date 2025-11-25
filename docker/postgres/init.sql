CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(120)
);

INSERT INTO users (name, email)
VALUES
('Justin', 'justin@example.com'),
('Maria', 'maria@example.com');

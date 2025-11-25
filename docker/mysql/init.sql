CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(120)
);

INSERT INTO users (name, email)
VALUES
('Justin', 'justin@example.com'),
('Carlos', 'carlos@example.com');

USE sample_db;

DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  total_spend DECIMAL(10, 2) NOT NULL,
  last_purchase TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  loyalty_tier ENUM('bronze', 'silver', 'gold', 'platinum') DEFAULT 'bronze'
);

INSERT INTO customers (name, email, total_spend, last_purchase, loyalty_tier) VALUES
  ('Alice Johnson', 'alice@example.com', 1200.50, '2024-06-01 10:15:00', 'gold'),
  ('Bob Smith', 'bob@example.com', 845.20, '2024-05-28 14:22:00', 'silver'),
  ('Carol Williams', 'carol@example.com', 4320.00, '2024-05-30 08:47:00', 'platinum'),
  ('David Miller', 'david@example.com', 220.75, '2024-04-18 16:05:00', 'bronze'),
  ('Eve Chen', 'eve@example.com', 1625.10, '2024-05-14 11:33:00', 'gold');

DROP TABLE IF EXISTS top_products;
CREATE TABLE top_products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(128) NOT NULL,
  total_sales INT NOT NULL,
  last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO top_products (name, category, total_sales, last_updated) VALUES
  ('Wireless Headphones', 'Electronics', 8750, '2024-05-31 09:00:00'),
  ('Espresso Machine', 'Home & Kitchen', 4210, '2024-05-29 15:45:00'),
  ('Trail Running Shoes', 'Sportswear', 6520, '2024-05-25 13:05:00');

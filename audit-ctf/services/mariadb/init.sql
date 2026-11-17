-- The application DB user, granted FILE (over-privileged — the audit finding).
CREATE USER IF NOT EXISTS 'appuser'@'%' IDENTIFIED BY 'appuser';
GRANT FILE ON *.* TO 'appuser'@'%';
GRANT ALL PRIVILEGES ON ctf.* TO 'appuser'@'%';
FLUSH PRIVILEGES;

CREATE TABLE IF NOT EXISTS ctf.orders (id INT, item VARCHAR(64), total DECIMAL(10,2));
INSERT INTO ctf.orders VALUES (1,'widget',9.99),(2,'gadget',19.99),(3,'sprocket',4.50);

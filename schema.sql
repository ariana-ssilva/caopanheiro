CREATE DATABASE IF NOT EXISTS caopanheiro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE caopanheiro;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, photo_filename VARCHAR(255),
  role ENUM('adopter','ong','admin') NOT NULL DEFAULT 'adopter',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE animals (
  id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL,
  species VARCHAR(40) NOT NULL, age VARCHAR(40), size VARCHAR(30),
  description TEXT, health TEXT, breed VARCHAR(80), sex VARCHAR(30),
  vaccinated VARCHAR(30), neutered VARCHAR(30), photo_filename VARCHAR(255),
  status ENUM('available','adopted','inactive') NOT NULL DEFAULT 'available',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE adoptions (
  id INT AUTO_INCREMENT PRIMARY KEY, animal_id INT NOT NULL, adopter_id INT NOT NULL,
  message TEXT, answers TEXT, status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (animal_id) REFERENCES animals(id), FOREIGN KEY (adopter_id) REFERENCES users(id)
);
CREATE TABLE feedback (
  id INT AUTO_INCREMENT PRIMARY KEY, adoption_id INT NOT NULL,
  rating TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5), comment TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (adoption_id) REFERENCES adoptions(id)
);

CREATE TABLE IF NOT EXISTS donations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  donor_id INT NOT NULL,
  kind VARCHAR(30) NOT NULL,
  amount DECIMAL(10,2),
  description TEXT NOT NULL,
  contact VARCHAR(180),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (donor_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS donation_events (
  id INT AUTO_INCREMENT PRIMARY KEY,
  donation_id INT NOT NULL,
  actor_id INT,
  status VARCHAR(20) NOT NULL,
  note TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (donation_id) REFERENCES donations(id),
  FOREIGN KEY (actor_id) REFERENCES users(id)
);

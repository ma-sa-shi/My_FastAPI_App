CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_admin BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delete_flg BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS docs (
    doc_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    dir_path VARCHAR(255),
    filename VARCHAR(100) NOT NULL,
    status ENUM("uploaded", "processing", "completed", "failed") DEFAULT "uploaded",
    extracted_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delete_flg BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
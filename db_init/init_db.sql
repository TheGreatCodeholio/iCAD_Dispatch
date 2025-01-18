-- create table users
CREATE TABLE `users`
(
    `user_id`       int(11) AUTO_INCREMENT PRIMARY KEY,
    `user_username` varchar(255) NOT NULL,
    `user_password` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- create app configuration table --
CREATE TABLE `app_config`
(
    `config_id`                    int(11) AUTO_INCREMENT PRIMARY KEY,
    `config_key`                   varchar(64) DEFAULT NULL,
    `config_value`                 varchar(64) DEFAULT NULL,
    `description`                  TEXT DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

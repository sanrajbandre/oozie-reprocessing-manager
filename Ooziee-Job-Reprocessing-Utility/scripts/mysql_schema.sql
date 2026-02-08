-- Create database manually if needed:
-- CREATE DATABASE oozie_reprocess CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE oozie_reprocess;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(128) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'viewer',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS plans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  oozie_url VARCHAR(512),
  use_rest BOOLEAN NOT NULL DEFAULT FALSE,
  max_concurrency INT NOT NULL DEFAULT 1,
  created_by VARCHAR(128),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tasks (
  id INT AUTO_INCREMENT PRIMARY KEY,
  plan_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  type VARCHAR(32) NOT NULL,
  job_id VARCHAR(128) NOT NULL,

  action VARCHAR(128),
  date VARCHAR(128),
  coordinator VARCHAR(255),

  wf_failnodes BOOLEAN NOT NULL DEFAULT FALSE,
  wf_skip_nodes VARCHAR(1024),

  refresh BOOLEAN NOT NULL DEFAULT FALSE,
  failed BOOLEAN NOT NULL DEFAULT FALSE,

  extra_props JSON,

  status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  attempt INT NOT NULL DEFAULT 0,

  command TEXT,
  stdout MEDIUMTEXT,
  stderr MEDIUMTEXT,
  exit_code INT,
  pid INT,

  started_at DATETIME,
  ended_at DATETIME,

  CONSTRAINT fk_tasks_plan FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_tasks_plan_status ON tasks(plan_id, status);
CREATE INDEX idx_plans_status ON plans(status);
CREATE INDEX idx_tasks_status ON tasks(status);

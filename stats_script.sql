DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS servers;
DROP TABLE IF EXISTS status;
DROP TABLE IF EXISTS names;
DROP TABLE IF EXISTS games;
PRAGMA foreign_keys = ON;
CREATE TABLE users (
  user_id integer NOT NULL,
  current_name text,
  PRIMARY KEY (user_id)
);
CREATE TABLE servers (
  server_id integer NOT NULL,
  user_id integer NOT NULL,
  PRIMARY KEY (server_id, user_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE TABLE status (
  user_id integer NOT NULL,
  online integer NOT NULL DEFAULT 0,
  idle integer NOT NULL DEFAULT 0,
  busy integer NOT NULL DEFAULT 0,
  offline integer NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE TABLE names (
  user_id integer NOT NULL,
  name text NOT NULL,
  PRIMARY KEY (user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE TABLE games (
  user_id integer NOT NULL,
  game_name text NOT NULL,
  time integer NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, game_name),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
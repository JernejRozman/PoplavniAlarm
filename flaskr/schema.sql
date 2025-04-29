DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS post;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE post (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  FOREIGN KEY (author_id) REFERENCES user (id)
);


-- Seznam e-pošt, na katere pošiljamo alarme
CREATE TABLE IF NOT EXISTS alert_email (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL,
    email    TEXT    NOT NULL,
    UNIQUE(user_id, email),
    FOREIGN KEY (user_id) REFERENCES user(id)
);


-- Pragovi vodostaja po uporabnikih
CREATE TABLE IF NOT EXISTS river_threshold (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    location     TEXT    NOT NULL,
    threshold_cm INTEGER NOT NULL,
    UNIQUE(user_id, location),           -- en zapis na (uporabnik, lokacija)
    FOREIGN KEY (user_id) REFERENCES user(id)
);

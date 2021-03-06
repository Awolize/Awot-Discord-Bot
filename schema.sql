DROP TABLE IF EXISTS servers;
DROP TABLE IF EXISTS status;
DROP TABLE IF EXISTS names;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS tvseries;
DROP TABLE IF EXISTS birthday;
DROP TABLE IF EXISTS spotify;
DROP TABLE IF EXISTS users;

CREATE TABLE users(
    user_id     BIGINT NOT NULL,
    name        TEXT,

    PRIMARY KEY (user_id)
);

CREATE TABLE servers(
    server_id  BIGINT NOT NULL,
    user_id    BIGINT NOT NULL,

    PRIMARY KEY (server_id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE server_info(
    server_id   BIGINT NOT NULL,
    users       INT    NOT NULL,
    t           TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP(0),

    PRIMARY KEY (server_id, t)
);

CREATE TABLE status(
    user_id    BIGINT NOT NULL,
    online     INT NOT NULL DEFAULT 0,
    idle       INT NOT NULL DEFAULT 0,
    dnd        INT NOT NULL DEFAULT 0,
    offline    INT NOT NULL DEFAULT 0,

    PRIMARY KEY (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE games(
    user_id     BIGINT NOT NULL,
    game        TEXT NOT NULL,
    play_time   INT NOT NULL DEFAULT 0,

    PRIMARY KEY (user_id, game),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

SET timezone = 'utc';
CREATE TABLE spotify(
    user_id         BIGINT  NOT NULL,
    title           TEXT    NOT NULL,
    album           TEXT    NOT NULL,
    artist          TEXT    NOT NULL,
    track_id        TEXT    NOT NULL,
    song_length     INT     NOT NULL,
    play_time       INT     DEFAULT 0,
    t               TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP(0),
    album_cover_url TEXT    NOT NULL,

    PRIMARY KEY (user_id, track_id, t),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE tvseries(
    user_id    BIGINT NOT NULL,
    name       TEXT NOT NULL,
    episode    INT DEFAULT 1,
    season     INT DEFAULT 1,

    PRIMARY KEY (user_id, name),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE birthday(
    user_id   BIGINT NOT NULL,
    server_id BIGINT NOT NULL,
    birthday  DATE NOT NULL,

    PRIMARY KEY (user_id, server_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
); 

CREATE TABLE pings(
    ping     	INT NOT NULL,
	t          	TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP(0),
    PRIMARY KEY (ping, t)
);
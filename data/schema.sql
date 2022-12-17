/* CREATE statements for relevant database tables.                            */
/* ************************************************************************** */

DROP TABLE player_settings;
DROP TABLE playlist_tracks;
DROP TABLE banners;
DROP TABLE banner_settings;

/* Music and playlist tables.                                                 */
/* ************************************************************************** */

CREATE TABLE IF NOT EXISTS player_settings (
    "guild_id"  BIGINT NOT NULL,    /* id of the guild      */
    "position"  INT,                /* playlist position    */
    "order"     TEXT NOT NULL,      /* playlist order       */
    "repeat"    TEXT NOT NULL,      /* playlist repeat mode */
    "volume"    INT NOT NULL        /* volume in %          */
);

ALTER TABLE player_settings
    ADD CONSTRAINT pk_player_settings
    PRIMARY KEY (guild_id);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    "guild_id"   BIGINT NOT NULL,   /* id of the guild                    */
    "user_id"    BIGINT NOT NULL,   /* requester id                       */
    "position"   INT NOT NULL,      /* position of the track in the queue */
    "type"       INT NOT NULL,      /* youtube, youtube_music, soundcloud */
    "identifier" TEXT NOT NULL      /* base64 identifier used by wavelink */
);

ALTER TABLE playlist_tracks 
    ADD CONSTRAINT pk_playlist_tracks
    PRIMARY KEY (guild_id, position);

/* Banner tables.                                                             */
/* ************************************************************************** */

CREATE TABLE IF NOT EXISTS banner_settings (
    "guild_id" BIGINT NOT NULL,                 /* id of the guild */
    "enabled" BOOLEAN NOT NULL DEFAULT FALSE,   /* whether banner rotation is enabled */
    "interval" BIGINT NOT NULL DEFAULT 30,      /* change interval in seconds. */
    "last_change" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP 
);

ALTER TABLE banner_settings
    ADD CONSTRAINT pk_banner_settings
    PRIMARY KEY (guild_id);

CREATE TABLE IF NOT EXISTS banners (
    "guild_id" BIGINT NOT NULL, /* id of the guild */
    "user_id" BIGINT NOT NULL,  /* id of the user that added the banner */
    "url" TEXT NOT NULL,        /* url of the image */
    "id" SERIAL                 /* serial for sorting */
);

ALTER TABLE banners
    ADD CONSTRAINT pk_banners
    PRIMARY KEY (guild_id, url);

/* Permissions.                                                               */
/* ************************************************************************** */

GRANT ALL ON TABLE banner_settings TO vibingway;
GRANT ALL ON TABLE banners         TO vibingway;
GRANT ALL ON TABLE player_settings TO vibingway;
GRANT ALL ON TABLE playlist_tracks TO vibingway;

ALTER TABLE banner_settings OWNER TO vibingway;
ALTER TABLE banners         OWNER TO vibingway;
ALTER TABLE player_settings OWNER TO vibingway;
ALTER TABLE playlist_tracks OWNER TO vibingway;
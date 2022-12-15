/* CREATE statements for relevant database tables. */

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

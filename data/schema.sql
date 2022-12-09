/* CREATE statements for relevant database tables. */

/* The queue_setings table holds extra information about music queues.
 * Used to restore queue settings after restarts or disconnects.
 */
CREATE TABLE IF NOT EXISTS queue_settings (
    "guild_id"  BIGINT NOT NULL,    
    "position"  INT,                /* last queue position */
    "order"     TEXT NOT NULL,      /* normal, reverse, random */
    "loop"      TEXT NOT NULL,       /* off, all, track */
    "volume"    INT NOT NULL        /* volume in percent (0 - 100) */
);

ALTER TABLE queue_settings
    ADD CONSTRAINT pk_queue_settings
    PRIMARY KEY (guild_id);

/* The queue_entries table holds all tracks currently in the queue.
 * Used to restore the queue after restarts or disconnects.
*/
CREATE TABLE IF NOT EXISTS queue_entries (
    "guild_id"   BIGINT NOT NULL,
    "user_id"    BIGINT NOT NULL,
    "position"   INT NOT NULL,      /* Position of the track in the queue. */
    "type"       INT NOT NULL,     /* youtube, soundcloud */
    "identifier" TEXT NOT NULL      /* base64 identifier used by wavelink */
);

ALTER TABLE queue_entries 
    ADD CONSTRAINT pk_queue_entries
    PRIMARY KEY (guild_id, position);


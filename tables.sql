CREATE TABLE IF NOT EXISTS nsv_table (
    discord_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    nation VARCHAR(50) NOT NULL,
    status VARCHAR(10) NOT NULL,
    UNIQUE (discord_id, guild_id)
);

CREATE TABLE IF NOT EXISTS nsv_settings (
    guild_id BIGINT,
    guest_role BIGINT,
    resident_role BIGINT,
    wa_resident_role BIGINT,
    verified_role BIGINT,
    region TEXT,
    welcome_message TEXT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS nation_dump (
    nation VARCHAR(50) NOT NULL,
    region VARCHAR(1000) NOT NULL,
    unstatus VARCHAR(15) NOT NULL,
    endorsements TEXT,
    last_update TIMESTAMP NOT NULL,
    PRIMARY KEY (nation)
);

CREATE TABLE IF NOT EXISTS welcome_settings (
    guild_id BIGINT,
    welcome_channel BIGINT,
    welcome_enabled BOOLEAN,
    PRIMARY KEY (guild_id)
);
)
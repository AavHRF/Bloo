CREATE TABLE IF NOT EXISTS nsv_table (
    discord_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    nation VARCHAR(50) NOT NULL,
    status VARCHAR(15) NOT NULL,
    UNIQUE (discord_id, guild_id)
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT,
    administrator_role BIGINT,
    moderator_role BIGINT,
    admin_channel BIGINT,
    log_channel BIGINT
);

CREATE TABLE IF NOT EXISTS nsv_settings (
    guild_id BIGINT NOT NULL DEFAULT 0,
    guest_role BIGINT NOT NULL DEFAULT 0,
    resident_role BIGINT NOT NULL DEFAULT 0,
    wa_resident_role BIGINT NOT NULL DEFAULT 0,
    verified_role BIGINT NOT NULL DEFAULT 0,
    region TEXT,
    welcome_message TEXT NOT NULL DEFAULT 'Welcome to the server!',
    force_verification BOOLEAN NOT NULL DEFAULT FALSE,
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
    welcome_channel BIGINT DEFAULT 0,
    welcome_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ping_on_join BOOLEAN NOT NULL DEFAULT FALSE,
    embed_message VARCHAR(500) DEFAULT 'Welcome to the server!',
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS nsv_ban_table(
    guild_id BIGINT NOT NULL,
    nation VARCHAR(50) NOT NULL,
    reason VARCHAR(1000) NOT NULL,
    UNIQUE (nation, guild_id)
);

CREATE TABLE IF NOT EXISTS react_roles (
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    emoji VARCHAR(50) NOT NULL,
    UNIQUE (guild_id, message_id, emoji)
);

CREATE TABLE IF NOT EXISTS nsl_table (
    discord_id BIGINT,
    nation VARCHAR(50),
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS nsl_region_table (
    region VARCHAR(1000),
    founder VARCHAR(50),
    wa_delegate VARCHAR(50),
    delegatevotes INTEGER,
    numnations INTEGER,
    inserted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    ticketcount BIGSERIAL,
    user_id BIGINT NOT NULL,
    response_id VARCHAR(50) NOT NULL,
    filed_at TIMESTAMP NOT NULL,
    PRIMARY KEY (ticketcount)
);

CREATE TABLE IF NOT EXISTS warn_table (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason VARCHAR(1000) NOT NULL,
    warned_by BIGINT NOT NULL,
    warned_at TIMESTAMP NOT NULL,
    UNIQUE (user_id, guild_id, warned_at)
);

CREATE TABLE IF NOT EXISTS watchlist (
    internal_id SERIAL PRIMARY KEY,
    primary_name VARCHAR(50) NOT NULL,
    reasoning TEXT NOT NULL,
    known_ids TEXT NOT NULL,
    known_names TEXT NOT NULL,
    known_nations TEXT NOT NULL,
    evidence TEXT NOT NULL,
    date_added TIMESTAMP NOT NULL
);
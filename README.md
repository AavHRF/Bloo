# Bloo

[Support Server](https://discord.gg/tFVVrAZErq) | [Invite Bloo](https://ptb.discord.com/api/oauth2/authorize?client_id=1033625714483806269&permissions=8&scope=applications.commands%20bot) 

Welcome to the repository for Bloo, a Discord bot for NationStates. If you're interested in running your own instance, read on, however, 
this repository is primarily hosted in accordance with the [site staff policy](https://forum.nationstates.net/viewtopic.php?p=40690135#p40690135) on scripting and technical
development as a staff member.

Pull requests welcome. They may not be accepted if they are not in line with the goals of the developer.

If you notice a security vulnerability, please contact the developer immediately. Do not post it publicly. You can do so
either via Discord (@queerlyfe) or via [telegram on NationStates.](https://www.nationstates.net/page=compose_telegram?tgto=united_calanworie&message=Bloo%20Security%20Vulnerability)
Pull requests to fix security vulnerabilities are welcome, but should be coordinated with the developer to ensure user safety.

Setup instructions:
- Install Python 3.11
- Install [Poetry](https://python-poetry.org)
- Install [PostgreSQL](https://www.postgresql.org) version 12.16 or higher
- Run `poetry install`
  - Dependencies (check [pyproject.toml](pyproject.toml) for versions):
    - discord.py
    - asyncpg
    - aiolimiter
    - openpyxl
  - * for compatibility/ease of use reasons, [`requirements.txt`](requirements.txt) has been added for `pip -m venv` usage. While not encouraged compared to poetry, it is a viable option.
- Run `./start.sh`. The tables should be automatically built from [tables.sql](tables.sql).
  - `./start.sh` depends on either `poetry` being installed, __or__ your pip-based virtual environment being in a folder called `venv` in the main directory for Bloo. If neither of those conditions apply, you're on your own.

You must supply a configuration file named `config.json` in the root folder of the repository once you have cloned it. It should look something like the following:
```json
{
    "token": "discord_token",
    "dsn": "postgres://username:password@localhost:5432/bloo"
}

```

Please note that future updates to the bot may add new line items to `config.json`. It is your responsibility to keep your config file up to date. A best-effort attempt will be made by the developer to keep this example up to date, but it may not always happen.

You will have to create the database `bloo` in your postgres install before running the bot. You can do this with the following command:
```sql
CREATE DATABASE bloo;
```

It's suggested that you create a user named `bloo` and give it access to the database. You can do this with the following commands:
```sql
CREATE USER bloo WITH PASSWORD 'YOUR PASSWORD HERE';
GRANT ALL PRIVILEGES ON DATABASE bloo TO bloo;
```

If you don't do that, you can instead provide your own user account's credentials in the DSN string. This is not recommended for security reasons.
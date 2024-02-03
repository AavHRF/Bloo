Bloo needs a privacy policy. To that extent, this is that document. It is a semi-formal outline of data storage and privacy practices.

Bloo collects almost no data about anything that happens on your Discord server. Command failures are logged fairly generically in a single logfile. They include the user ID that triggered the failure, the server ID, and the channel ID. If command parameters were supplied, they may be recorded as well. This logfile is purged whenever the bot is restarted (I think?), or sooner if the bot generates enough events to force a log handler rotation. 

Bloo does not store message content from any server. 

Bloo stores the following information:
- Guild NSV & welcome settings
- User <-> Nation relationships
- Any bans you (the server administrator) have made through the NSV bans system
- A record of any ticket that you create through the bot

If you wish to have your data purged, please contact the developer, either through the PM system on this forum, Discord DM (Aav#7546), or filing a ticket with the `/ticket` command. Please provide user/server IDs where relevant. Most commands also contain the ability to remove their information through some other mechanism (e.g. the `/drop_nation` command, or entering blank preferences into server/welcome settings.)

This policy may be updated at any time as found useful/relevant/important by the developer. If you have questions, feel free to ask in this thread.

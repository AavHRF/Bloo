# Bloo NS Verification Bot

Bloo provides simple, easy to configure NS verification to enable server administrators to tie a nation to a Discord user per server. 

Onto the documentation:

`[parameter]` is a required parameter
`{parameter}` is an optional parameter

* `/settings`, enabling a server administrator to configure NSV settings for the server
Menu options:
  * Verified role: This is the role that all members in the server who verify their nation should receive
  * Guest role: Non-resident members of the server will receive this role on verification
  * Resident role: Any verified member with a nation in your region will receive this role
  * WA Resident role: Similar to above, but with the added criteria of WA membership
  * Set region: Spawns a dialogue box to input the region for your server -- required in order to process verifications properly. You can provide a comma-separated list of regions should you wish to allow more than one region to receive a role.
  * Set verification DM message: Set the message received upon verifying a nation in the server
* `/verify [nation name]`, enabling a user to verify a nation for use on that server
  * You must be accepting DMs from all users. If you are not, Bloo will silently fail on you.
* `/drop`, dropping a nation from ownership in that server freeing a user to verify another
* `/info {member}`, allowing anyone to bring up a small infobox about a user which includes their nation
* `/post [channel] [message] {message ID}`
  * If you provide a message ID, Bloo will attempt to edit that message instead
* `/welcome`
Menu options:
  * Set welcome channel: Pick a channel in your server to have the messages sent in
  * Enable/disable leave/join messages: What it says on the tin
  * Enable/disable ping on join: toggles whether or not the welcome embed should be sent with a "ping" (@user) of the user
  * Set join message: Configure the message in the welcome embed, 500 character max
* `/purge`
  * Kick all unverified users from your server in one swift and decisive fireball
* `/ban_nation [nation] [reason] {delete message days}`
  * Ban a user with the provided nation from joining your Discord server, or, should they already be present, remove them from the server... with prejudice. Optionally, set a number of days of messages to delete
* `/lookup [type] [name] [who to show]`
  * Look up a nation or region by name. If "who to show" is set to "me," and you have the `BAN_MEMBERS` permission, you can see if the provided nation has been banned from your server, and if so, why
* `/ticket [category] [title] [description] {image attachment}`
  * Files a ticket with the developer (that's me!) through Discord.


This is the end of the documentation. There is no more. If you made it this far, and have questions like "why did you do this," or "help," or "I fucked up send help," or "AAAAAAAAAAAAAAA," feel free to join the [Bloo Support Server.](https://discord.gg/tFVVrAZErq) 

Here is the [invite link](https://discord.com/api/oauth2/authorize?client_id=1033625714483806269&permissions=8&scope=bot%20applications.commands) for Bloo. She asks for the Administrator permission. If you want, you can knock that permission set down to just Manage Roles, Kick Members, Ban Members, and standard user permissions, but you will likely break future features that will gradually roll out. If you're okay with that and will hand out the permissions when you need them, that's okay too. But if you come and ask for help later on, I will likely just tell you to give her admin to fix the problems. 

Please make sure that Bloo's role is at the top of your role list, or at the very least, above the roles you want her to manage. Otherwise she will silently fail (not so silently in my console) and you will be frustrated.

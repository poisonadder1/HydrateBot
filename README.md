# HydrateBot
A simple bot for discord that remindes people who are in a vc to hydrate every so often. If a person leaves and rejoins vc within a certain time period the reminder will still be given as if they had not left, however, it will not notify if they aren't in vc when the reminder is due but will instead wait til they have rejoined vc.

Requires python3 with discord.py and psycopg2 and a postresql database

The bot will react to the following messages, "$helloHB" (a simple test message), "$vcTextChannel" (set currect channel for hydration reminders), "$setupHB:{timeout duration in whole minutes},{time between hydration reminders in whole minutes}" to configure how long to remember a member in case of a leave and re-join and how often to remind people to hydrate. The reminders will be processed every 60s and send if a person has been in vc for longer than the designated time, this means that if the reminder frequancy is set to 30 minutes the reminder will be delivered between 30 and 31 minutes

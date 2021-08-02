import discord, logging, psycopg2, datetime
from discord.ext import tasks

#Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#Define the required intents (requred to register for events
intents = discord.Intents(messages=True, voice_states=True, guilds=True)
intents.members = True


#Database connection configuration
dbaddres = ''
dbport = ''
dbuser = ''
dbpass = ''
dbname = ''

class HydrateBotClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # start the background tasks
        self.check_hydration_requirement.start()
    
    #Ready message
    async def on_ready(self):
        print("We have logged in as {0.user}".format(client))
        #TODO tidy stuff up from last session???

    #React to message
    async def on_message(self, message):
        if message.author == client.user:
            return
        
        #Hello World test message
        if message.content.startswith("$helloHB"):
            msgText = "Hello! <@" + str(message.author.id) + ">"
            await message.channel.send(msgText)
        
        #Setup text channel for notifications
        if message.content.startswith('$vcTextChannel'):
            if message.author.guild_permissions.administrator:
                #See if channel is already set
                guildID = message.guild.id
                channelID = message.channel.id
                conn = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
                cur = conn.cursor()
                cur.execute("SELECT vctextchannelid FROM guildsettings WHERE guildid=%s",(str(guildID), ))
                if cur.rowcount>0:
                    row = cur.fetchone()
                    oldChannelID = row[0]
                    if str(oldChannelID) == str(channelID):
                        await message.channel.send("VC text channel already set to current channel, no changes made")
                        cur.close()
                        conn.close()
                    else:
                        cur.execute("UPDATE guildsettings SET vctextchannelid=%s WHERE guildid=%s", (str(channelID), str(guildID)))
                        conn.commit()
                        cur.close()
                        conn.close()
                        await message.channel.send("VC text channel updated to current channel")
                else:
                    cur.execute("INSERT INTO guildsettings (guildid, timeoutduration, remindertime, vctextchannelid) VALUES (%s, %s, %s, %s)", (str(guildID), 2*60, 30*60, str(channelID)))
                    conn.commit()
                    cur.close()
                    conn.close()
                    await message.channel.send("VC text channel set to current channel, use $setupHB to configure the other settings")
            else:
                await message.channel.send("Sorry you don't have permissions to do that, you must be a server administrator")
        
        if message.content.startswith('$setupHB'):
            if message.author.guild_permissions.administrator:
                msgText = message.content
                if (msgText.find(":") == -1) or (msgText.find(",") == -1):
                    await message.channel.send("To setup the bot type '$setupHB:{timeout duration in whole minutes},{time between hydration reminders in whole minutes}' e.g, '$setupHB:2,30'")
                else:
                    timeoutDuration = int(msgText[msgText.find(":")+1:msgText.find(",")]) * 60
                    reminderTime = int(msgText[msgText.find(",")+1:]) * 60
                    guildID = message.guild.id
                    conn = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
                    cur = conn.cursor()
                    cur.execute("SELECT guildid FROM guildsettings WHERE guildid=%s",(str(guildID), ))
                    if cur.rowcount>0:
                        cur.execute("UPDATE guildsettings SET timeoutduration=%s,remindertime=%s WHERE guildid=%s", (timeoutDuration, reminderTime, str(guildID)))
                        conn.commit()
                        cur.close()
                        conn.close()
                        await message.channel.send("Settings updated")
                    else:
                        cur.execute("INSERT INTO guildsettings (guildid, timeoutduration,remindertime) WHERE guildid=%s", (timeoutDuration, reminderTime, str(guildID)))
                        conn.commit()
                        cur.close()
                        conn.close()
                        await message.channel.send("Settings configured")
            else:
                await message.channel.send("Sorry you don't have permissions to do that, you must be a server administrator")

    async def on_voice_state_update(self, member, before, after):
        if before.channel == None: #Joining VC
            conn = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
            cur = conn.cursor()
            #Check if member is already in the db
            cur.execute("SELECT member FROM vcmembers WHERE member=%s", (str(member.id), ))
            if cur.rowcount>0:
                cur.execute("UPDATE vcmembers SET vcleavetime=%s, vcchannelid=%s WHERE member=%s", (None, str(after.channel.id), str(member.id))) #most likely reason for joining vc when already in the db is left briefly and haas yet to be purged or moved vc channels within the purge period
                conn.commit()
                cur.close()
                conn.close()
            else: #otherwise add them to the db
                now = datetime.datetime.now()
                cur.execute("INSERT into vcmembers (member, lasthydrationreminder, vcchannelid) VALUES (%s, %s, %s)", (str(member.id), now, str(after.channel.id)))
                conn.commit()
                cur.close()
                conn.close()
        elif after.channel == None: #Leaving VC
            conn = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
            cur = conn.cursor()
            #Check if member is in the db (if not in the db do nothing)
            cur.execute("SELECT member FROM vcmembers WHERE member=%s", (str(member.id), ))
            if cur.rowcount>0:
                now = datetime.datetime.now()
                cur.execute("UPDATE vcmembers SET vcleavetime=%s WHERE member=%s", (now, str(member.id))) #set leave time so can be purged
                conn.commit()
                cur.close()
                conn.close()
            
        elif before.channel.id != after.channel.id: #changing vc channel
            conn = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
            cur = conn.cursor()
            #Check if member is already in the db and update their channel
            cur.execute("SELECT member FROM vcmembers WHERE member=%s", (str(member.id), ))
            if cur.rowcount>0:
                cur.execute("UPDATE vcmembers SET vcchannelid=%s WHERE member=%s", (str(after.channel.id), str(member.id)))
                conn.commit()
                cur.close()
                conn.close()
            else: #otherwise add them to the db, probably bot was down when vc joined
                now = datetime.datetime.now()
                cur.execute("INSERT into vcmembers (member, lasthydrationreminder, vcchannelid) VALUES (%s, %s, %s)", (str(member.id), now, str(after.channel.id)))
                conn.commit()
                cur.close()
                conn.close()

    @tasks.loop(seconds=60) #run task every 60s
    async def check_hydration_requirement(self):
        now = datetime.datetime.now()
        membersToRemind = []
        conn = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
        cur = conn.cursor()
        cur.execute("SELECT * FROM vcmembers")
        for row in cur:
            memberID = row[0]
            lastHydrationReminder = row[1]
            vcChannelID = row[2]
            timeLeftVC = row[3]
            if row[3] == None:
                timeSinceLastReminder = now - lastHydrationReminder
                #Get guild ID so can lookup reminder period
                guildID = self.get_guildID_from_vcChannelID(vcChannelID)
                #get settings for guild
                cur2 = conn.cursor()
                cur2.execute("SELECT remindertime from guildsettings WHERE guildid=%s", (str(guildID), ))
                if cur2.rowcount>0:
                    reminderTime = cur2.fetchone()[0]
                else:
                    print("Unable to load guild settings for " + str(guildID))
                    continue
                
                #Check if reminder needed
                if timeSinceLastReminder.total_seconds() > reminderTime:
                    #check if still in vc
                    guild = self.get_guild(int(guildID))
                    vcChannel = guild.get_channel(int(vcChannelID))
                    for member in vcChannel.members:
                        if str(member.id) == memberID:
                            membersToRemind.append([guildID, memberID])
                            cur2.execute("UPDATE vcmembers SET lasthydrationreminder=%s WHERE member=%s", (now, memberID))
                            conn.commit()
                            break
                    else: #if not found in vc purge from db
                        cur2.execute("DELETE FROM vcmembers WHERE member=%s", (memberID, ))
                        conn.commit()
                
            else: 
                #Check if needed to purge
                timeSinceLeftVC = now - timeLeftVC
                #Get guild ID so can lookup timeout period
                guildID = self.get_guildID_from_vcChannelID(vcChannelID)
                
                #get settings for guild
                cur2 = conn.cursor()
                cur2.execute("SELECT timeoutduration from guildsettings WHERE guildid=%s", (str(guildID), ))
                if cur2.rowcount>0:
                    timeoutDuration = cur2.fetchone()[0]
                else:
                    print("Unable to load guild settings for " + str(guildID))
                    continue
                if timeSinceLeftVC.total_seconds() > timeoutDuration:
                    cur2.execute("DELETE FROM vcmembers WHERE member=%s", (memberID, ))
                    conn.commit()
                cur2.close()
        
        #TODO send message
        membersToRemind.sort(key=lambda member: member[1])
        
        msgText = "Remember to hydrate"
        while len(membersToRemind) > 0:
            if len(membersToRemind) > 1:
                [guildID, memberID] = membersToRemind.pop()
                msgText = msgText + " <@" + memberID + ">"
                #msgText = "Hello! <@" + str(message.author.id) + ">"
                if guildID != membersToRemind[-1][0]:
                    cur2.execute("SELECT vctextchannelid from guildsettings WHERE guildid=%s", (str(guildID), ))
                    if cur2.rowcount > 0:
                        vcTextChannelID = cur2.fetchone()[0]
                        if vcTextChannelID != None:
                            #TODO send notification message
                            vcTextChannel = self.get_channel(int(vcTextChannelID))
                            await vcTextChannel.send(msgText)
                    
                    #initialise msgText for next loop
                    msgText = "Remember to hydrate"
            else:
                [guildID, memberID] = membersToRemind.pop()
                msgText = msgText + " <@" + memberID + ">"
                cur2.execute("SELECT vctextchannelid from guildsettings WHERE guildid=%s", (str(guildID), ))
                if cur2.rowcount > 0:
                    vcTextChannelID = cur2.fetchone()[0]
                    if vcTextChannelID != None:
                        #TODO send notification message
                        vcTextChannel = self.get_channel(int(vcTextChannelID))
                        await vcTextChannel.send(msgText)
        
        cur.close()
        conn.close()
        
    
    @check_hydration_requirement.before_loop
    async def before_task(self):
        await self.wait_until_ready() # wait until the bot logs in
    
    def get_guildID_from_vcChannelID(self, vcChannelID):
        connLocal = psycopg2.connect("host=" + dbaddres + " port=" + dbport + " dbname=" + dbname + " user=" + dbuser + " password=" + dbpass)
        curLocal = connLocal.cursor()
        curLocal.execute("SELECT guildid from vcchannels WHERE vcchannelid=%s", (str(vcChannelID), ))
        if curLocal.rowcount>0:
            guildID = curLocal.fetchone()[0]
            return guildID
        else:
            #search for vc channels
            channelFound = False
            for guild in self.guilds:
                guildID = guild.id
                for vcChannel in guild.voice_channels: #vcChannel.id
                    #Check if channel id is a match
                    if str(vcChannelID) == str(vcChannel.id):
                        curLocal.execute("INSERT into vcchannels (vcchannelid, guildid) VALUES (%s, %s)", (str(vcChannelID), str(guildID)))
                        connLocal.commit()
                        channelFound = True
                        break
                if channelFound:
                    break
            curLocal.execute("SELECT guildid from vcchannels WHERE vcchannelid=%s", (str(vcChannelID), ))
            if curLocal.rowcount>0:
                guildID = curLocal.fetchone()[0]
                curLocal.close()
                connLocal.close()
                return guildID
            else:
                curLocal.close()
                connLocal.close()
                return None

client = HydrateBotClient(intents=intents)
client.run("")

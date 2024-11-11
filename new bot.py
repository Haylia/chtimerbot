import discord
import os
import time
import random
import gspread
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

from discord.ext import commands, tasks
from discord import guild, embeds, Embed, InteractionResponse
from discord.utils import get
intents = discord.Intents.all()
bot_activity = discord.Game(name = "with time")
client = commands.Bot(command_prefix = '?', intents = intents, case_insensitive = True, activity = bot_activity)

def toBool(string):
    string = string.capitalize()
    if string == "True":
        return True
    else:
        return False

bosstimes = []
bossnames = []
privatetimes = []
privatenames = []
approvedservers = []
privateservers = []
currenttimers = []
timerlastupdate = 0

with open('APPROVEDSERVERS.txt', 'r') as f:
    for server in f.readlines():
        approvedservers.append(int(server.strip("\n")))

with open('PRIVATESERVERS.txt', 'r') as f:
    for server in f.readlines():
        privateservers.append(int(server.strip("\n")))

with open('BOSSTIMERS.txt', 'r') as f:
    filebosstimes = f.readlines()
    for b in filebosstimes:
        b = b.strip("\n")
        b = b.split(",")
        # (bossname, timer, window, catagory)
        bosstimes.append((b[0],float(b[1])*60,float(b[2])*60,b[3]))
        bossnames.append(b[0])

with open('PRIVATETIMERS.txt', 'r') as f:
    filebosstimes = f.readlines()
    for b in filebosstimes:
        b = b.strip("\n")
        b = b.split(",")
        # (bossname, timer, window, catagory)
        privatetimes.append((b[0],float(b[1])*60,float(b[2])*60,b[3]))
        privatenames.append(b[0])

f = open("TIMERDUMP.txt", "r")
currenttimers = []
for line in f:
    line = line.strip("\n")
    line = line.split(",")
    line[1] = float(line[1])
    line[2] = float(line[2])
    line[3] = float(line[3])
    line[5] = toBool(line[5])
    line[6] = toBool(line[6])
    #not all the channels are in the same guild, so we need to get the channel object from the id
    line[7] = client.get_channel(int(line[7]))
    currenttimers.append(line)
f.close()




@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guilds in client.guilds:
        print(f'Connected to {guilds.name} - {guilds.id}')
    print(f'Approved servers: {approvedservers}')
    #run the load function to load the timers from the file
    timerloop.start()
    refreshloop.start()
    # filedump.start()

@client.event
async def on_message(message):
    global currenttimers
    if message.author == client.user:
        return
    if (int(message.guild.id) not in approvedservers and int(message.guild.id) not in privateservers):
        print(f'{message.guild.name} is not an approved server')
        return
    # print(f'{message.guild} - {message.channel} - {message.author}: {message.content}, {time.time()}')

    if message.author.id == 278288658673434624 and message.content.lower().split(" ")[0] == 'announcement' and message.content.lower().split(" ")[1] == 'allservers':
        # find all unique return channels in the currenttimers list
        returnchannels = []
        messagetosend = message.content[23:]
        for c in currenttimers:
            if c[7] not in returnchannels:
                returnchannels.append(c[7])
        for rc in returnchannels:
            await rc.send("Announcement: " + messagetosend)
    
    if message.author.id == 278288658673434624 and message.content.lower().split(" ")[0] == 'announcement' and message.content.lower().split(" ")[1] == 'oneserver':
        returnchannelid = message.content.split(" ")[2]
        returnchannel = client.get_channel(int(returnchannelid))
        messagetosend = message.content[22:]
        await returnchannel.send("Announcement: " + messagetosend)


    if message.content.lower().split(" ")[0] == 'request':
        messagetosend = message.content[8:]
        getliastar = client.get_user(278288658673434624)
        await getliastar.send(messagetosend + " - " + message.author.name + " - " + message.guild.name + " - " + str(message.guild.id) + ", " + message.channel.name + " - " + str(message.channel.id))
        await message.channel.send("Request sent")


    messageguild = message.guild.id

    if message.content.lower().split(" ")[0] == 'coffee':
        coffeegifs = ['https://tenor.com/view/coffee-gif-14866884794849307214', 'https://tenor.com/view/time-coffee-coffee-cup-caf%C3%A9-tasse-gif-4796156711064082985','https://tenor.com/view/coffee-coffee-time-coffee-cup-morning-coffee-have-a-cup-of-coffee-gif-24577802','https://tenor.com/view/coffee-coffee-cup-tea-caffe-caffeine-gif-13667954778907566683','https://tenor.com/view/coffee-gif-8528563834402265597', 'https://tenor.com/view/coffee-coffee-meme-morning-meme-gif-4074330043303180910','https://tenor.com/view/hot-coffee-heure-cafe-jaime-le-caf%C3%A9-coffee-break-pause-cafe-gif-27441149','https://tenor.com/view/coffee-time-coffee-to-the-rescue-coffee-adulting-mornings-gif-7960266']
        await message.channel.send(random.choice(coffeegifs))

    #<t:1709433660:f>
    if message.content.lower().split(" ")[0] == 'soon':
        embed = discord.Embed(title = "Timer Dashboard", colour=discord.Color.blue())
        serveregs = []
        servermids = []
        serveredls = []
        serverdls = []
        serverrings = []
        servercustoms = []
        for c in currenttimers:
            if str(messageguild) in c[0] and c[4] == "EG":
                serveregs.append(c)
            if str(messageguild) in c[0] and c[4] == "MIDS":
                servermids.append(c)
            if str(messageguild) in c[0] and c[4] == "EDL":
                serveredls.append(c)
            if str(messageguild) in c[0] and c[4] == "DL":
                serverdls.append(c)
            if str(messageguild) in c[0] and c[4] == "RINGS":
                serverrings.append(c)
            if str(messageguild) in c[0] and c[4] == "CUSTOM":
                servercustoms.append(c)
        serveregs = sorted(serveregs, key=lambda x: x[1] + x[2])
        servermids = sorted(servermids, key=lambda x: x[1] + x[2])
        serveredls = sorted(serveredls, key=lambda x: x[1] + x[2])
        serverdls = sorted(serverdls, key=lambda x: x[1] + x[2])
        serverrings = sorted(serverrings, key=lambda x: x[1] + x[2])
        servercustoms = sorted(servercustoms, key=lambda x: x[1] + x[2])
        if len(serveregs) > 0:
            embed.add_field(name="Endgames",value="",inline=False)
            for e in serveregs:
                embed.add_field(name=e[0].replace(str(messageguild),""), value=f"Due <t:{int(e[1] + e[2])}:R> at <t:{int(e[1] + e[2])}:f> \n Max <t:{int(e[1] + e[2] + e[3])}:R> at <t:{int(e[1] + e[2] + e[3])}:f>", inline=False)
        if len(servermids) > 0:
            embed.add_field(name="Midgames",value="",inline=False)
            for m in servermids:
                embed.add_field(name=m[0].replace(str(messageguild),""), value=f"Due  <t:{int(m[1] + m[2])}:R> at <t:{int(m[1] + m[2])}:f>", inline=False)
        if len(serveredls) > 0:
            embed.add_field(name="EDLs",value="",inline=False)
            for e in serveredls:
                embed.add_field(name=e[0].replace(str(messageguild),""), value=f"Due <t:{int(e[1] + e[2])}:R> at <t:{int(e[1] + e[2])}:f>", inline=False)
        if len(serverdls) > 0:
            embed.add_field(name="DLs",value="",inline=False)
            for d in serverdls:
                embed.add_field(name=d[0].replace(str(messageguild),""), value=f"Due <t:{int(d[1] + d[2])}:R> at <t:{int(d[1] + d[2])}:f>", inline=False)
        if len(serverrings) > 0:
            embed.add_field(name="Rings",value="",inline=False)
            for r in serverrings:
                embed.add_field(name=r[0].replace(str(messageguild),""), value=f"Due <t:{int(r[1] + r[2])}:R> at <t:{int(r[1] + r[2])}:f>", inline=False)
        if len(servercustoms) > 0:
            embed.add_field(name="Customs",value="",inline=False)
            for c in servercustoms:
                embed.add_field(name=c[0].replace(str(messageguild),""), value=f"Due <t:{int(c[1] + c[2])}:R> at <t:{int(c[1] + c[2])}:f>", inline=False)
        embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
        await message.channel.send(embed=embed)

    if len(message.content.lower().split(" ")) == 2:
        if message.content.lower().split(" ")[0] == 'soon' and message.content.lower().split(" ")[1] == 'eg':
            embed = discord.Embed(title = "Endgame Timer Dashboard", colour=discord.Color.blue())
            serveregs = []
            for c in currenttimers:
                if str(messageguild) in c[0] and c[4] == "EG":
                    serveregs.append(c)
            serveregs = sorted(serveregs, key=lambda x: x[1] + x[2])
            if len(serveregs) > 0:
                embed.add_field(name="Endgames",value="",inline=False)
                for e in serveregs:
                    embed.add_field(name=e[0].replace(str(messageguild),""), value=f"Due <t:{int(e[1] + e[2])}:R> at <t:{int(e[1] + e[2])}:f> \n Max <t:{int(e[1] + e[2] + e[3])}:R> at <t:{int(e[1] + e[2] + e[3])}:f>", inline=False)
            embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
            await message.channel.send(embed=embed)
    
    
        if message.content.lower().split(" ")[0] == 'soon' and message.content.lower().split(" ")[1] == 'mids':
            embed = discord.Embed(title = "Midgame Timer Dashboard", colour=discord.Color.blue())
            servermids = []
            for c in currenttimers:
                if str(messageguild) in c[0] and c[4] == "MIDS":
                    servermids.append(c)
            servermids = sorted(servermids, key=lambda x: x[1] + x[2])
            if len(servermids) > 0:
                embed.add_field(name="Midgames",value="",inline=False)
                for m in servermids:
                    embed.add_field(name=m[0].replace(str(messageguild),""), value=f"Due  <t:{int(m[1] + m[2])}:R> at <t:{int(m[1] + m[2])}:f>", inline=False)
            embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
            await message.channel.send(embed=embed)
        
        if message.content.lower().split(" ")[0] == 'soon' and message.content.lower().split(" ")[1] == 'edl':
            embed = discord.Embed(title = "EDL Timer Dashboard", colour=discord.Color.blue())
            serveredls = []
            for c in currenttimers:
                if str(messageguild) in c[0] and c[4] == "EDL":
                    serveredls.append(c)
            serveredls = sorted(serveredls, key=lambda x: x[1] + x[2])
            if len(serveredls) > 0:
                embed.add_field(name="EDLs",value="",inline=False)
                for e in serveredls:
                    embed.add_field(name=e[0].replace(str(messageguild),""), value=f"Due <t:{int(e[1] + e[2])}:R> at <t:{int(e[1] + e[2])}:f>", inline=False)
            embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
            await message.channel.send(embed=embed)
        
        if message.content.lower().split(" ")[0] == 'soon' and message.content.lower().split(" ")[1] == 'dl':
            embed = discord.Embed(title = "DL Timer Dashboard", colour=discord.Color.blue())
            serverdls = []
            for c in currenttimers:
                if str(messageguild) in c[0] and c[4] == "DL":
                    serverdls.append(c)
            serverdls = sorted(serverdls, key=lambda x: x[1] + x[2])
            if len(serverdls) > 0:
                embed.add_field(name="DLs",value="",inline=False)
                for d in serverdls:
                    embed.add_field(name=d[0].replace(str(messageguild),""), value=f"Due <t:{int(d[1] + d[2])}:R> at <t:{int(d[1] + d[2])}:f>", inline=False)
            embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
            await message.channel.send(embed=embed)
    
        if message.content.lower().split(" ")[0] == 'soon' and (message.content.lower().split(" ")[1] == 'rings' or message.content.lower().split(" ")[1] == 'banes' or message.content.lower().split(" ")[1] == 'helis'):
            embed = discord.Embed(title = "Ring/Bane/Heli Timer Dashboard", colour=discord.Color.blue())
            serverrings = []
            for c in currenttimers:
                if str(messageguild) in c[0] and c[4] == "RINGS":
                    serverrings.append(c)
            serverrings = sorted(serverrings, key=lambda x: x[1] + x[2])
            if len(serverrings) > 0:
                embed.add_field(name="Rings",value="",inline=False)
                for r in serverrings:
                    embed.add_field(name=r[0].replace(str(messageguild),""), value=f"Due <t:{int(r[1] + r[2])}:R> at <t:{int(r[1] + r[2])}:f>", inline=False)
            embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
            await message.channel.send(embed=embed)

    if message.content.lower().split(" ")[0] in privatenames and message.guild.id in privateservers:
        if len(message.content.lower().split(" ")) == 2:
                try:
                    if message.content.lower().split(" ")[1][-1] == "m":
                        offset = int(message.content.lower().split(" ")[1][:-1])*60
                    else:
                        offset = 0
                except:
                    offset = 0
        else:
            offset = 0
        for b in privatetimes:
            if b[0] == message.content.lower().split(" ")[0]:
                await message.channel.send(f'{message.content.lower().split(" ")[0]} will be due at <t:{int(time.time() + b[1] - offset)}:f>')
                for c in currenttimers:
                    if c[0] == message.content.lower().split(" ")[0] + " " + str(messageguild):
                        currenttimers.remove(c)
                currenttimers.append([message.content.lower().split(" ")[0] + " " + str(messageguild),time.time(),b[1] - offset,b[2],b[3],False,False,message.channel])
                #bossname+serverid, starttime, timer, window, catagory, due, preping, sentchannel
                #0                  1          2      3       4         5    6      7
    elif message.content.lower().split(" ")[0] in bossnames:
        if len(message.content.lower().split(" ")) == 2:
                try:
                    if message.content.lower().split(" ")[1][-1] == "m":
                        offset = int(message.content.lower().split(" ")[1][:-1])*60
                    else:
                        offset = 0
                except:
                    offset = 0
        else:
            offset = 0
        for b in bosstimes:
            if b[0] == message.content.lower().split(" ")[0]:
                await message.channel.send(f'{message.content.lower().split(" ")[0]} will be due at <t:{int(time.time() + b[1] - offset)}:f>')
                for c in currenttimers:
                    if c[0] == message.content.lower().split(" ")[0] + " " + str(messageguild):
                        currenttimers.remove(c)
                currenttimers.append([message.content.lower().split(" ")[0] + " " + str(messageguild),time.time(),b[1] - offset,b[2],b[3],False,False,message.channel])
                #bossname+serverid, starttime, timer, window, catagory, due, preping, sentchannel
                #0                  1          2      3       4         5    6      7

    if message.content.lower().split(" ")[0] == "refresh":
        refreshtimers()
        formattedbosstimes = ""
        if message.guild.id in privateservers:
            for b in privatetimes:
                formattedbosstimes += f"{b[0]}: {b[1]/60}m, {b[2]/60}m\n"
        else:
            for b in bosstimes:
                formattedbosstimes += f"{b[0]}: {b[1]/60}m, {b[2]/60}m\n"
        await message.channel.send("Timers refreshed\n new boss timers are:\nName: Timer, Window\n" + str(formattedbosstimes))

    if message.content.lower().split(" ")[0] == "info":
        formattedbosstimes = ""
        if message.guild.id in privateservers:
            for b in privatetimes:
                formattedbosstimes += f"{b[0]}: {b[1]/60}m, {b[2]/60}m\n"
        else:
            for b in bosstimes:
                formattedbosstimes += f"{b[0]}: {b[1]/60}m, {b[2]/60}m\n"
        await message.channel.send("Boss timers are:\nName: Timer, Window\n" + str(formattedbosstimes))

    if message.content.lower().split(" ")[0] == "dump":
        f = open("TIMERDUMP.txt", "w")
        for c in currenttimers:
            for p in c:
                #if its the message channel, the last element, store the channel id instead of the channel object
                if p == c[7]:
                    f.write(str(p.id))
                else:
                    f.write(str(p) + ",")
            f.write("\n")
        f.close()
        await message.channel.send("Dumped current timers to file")

    if message.content.lower().split(" ")[0] == "load":
        f = open("TIMERDUMP.txt", "r")
        currenttimers = []
        for line in f:
            line = line.strip("\n")
            line = line.split(",")
            line[1] = float(line[1])
            line[2] = float(line[2])
            line[3] = float(line[3])
            line[5] = toBool(line[5])
            line[6] = toBool(line[6])
            #not all the channels are in the same guild, so we need to get the channel object from the id
            line[7] = client.get_channel(int(line[7]))
            currenttimers.append(line)
        f.close()
        await message.channel.send("Loaded current timers from file")

    if message.content.lower().split(" ")[0] == "refreshservers":
        refreshservers()
        await message.channel.send("Refreshed servers")
    
    await client.process_commands(message)


@client.command()
async def cleartimers(ctx):
    global currenttimers
    for c in currenttimers:
        if str(ctx.guild.id) in c[0]:
            currenttimers.remove(c)
    await ctx.send("Cleared all timers for this server")




@tasks.loop(seconds=5)
async def timerloop():
    global timerlastupdate
    timerlastupdate = time.time()
    try:
        for c in currenttimers:
            # print(c[0] + " " + str(c[1]) + " " + str(c[2]) + " " + str(c[3]) + " " + str(c[4]) + " " + str(c[5]) + " " + str(c[6]) + " " + str(c[7]))
            # print(c[1] + c[2] - 3*60)
            if "prot" in c[0] and c[6] == False and time.time() > c[1] + c[2] - 10*60:
                try:
                    find_role = discord.utils.get(c[7].guild.roles, name=c[4])
                    c[6] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due in 10 minutes ' + find_role.mention)
                except:
                    print("failed to find role" + c[4] + " in " + c[7].guild.name)
                    c[6] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due in 10 minutes')
            if c[6] == False and time.time() > c[1] + c[2] - 3*60 and c[7].id == 1232156695481024593 and c[0].split(" ")[0] == "215":
                try:
                    find_role = discord.utils.get(c[7].guild.roles, name="Unox")
                    find_role2 = discord.utils.get(c[7].guild.roles, name="EDL")
                    c[6] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due in 3 minutes ' + find_role.mention + " " + find_role2.mention)
                except:
                    print("failed to find role" + c[4] + " in " + c[7].guild.name)
                    c[6] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due in 3 minutes')
            if (c[4] == "DL" or c[4] == "EDL") and c[6] == False and time.time() > c[1] + c[2] - 3*60:
                try:
                    find_role = discord.utils.get(c[7].guild.roles, name=c[4])
                    c[6] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due in 3 minutes ' + find_role.mention)
                except:
                    print("failed to find role" + c[4] + " in " + c[7].guild.name)
                    c[6] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due in 3 minutes')
            if time.time() > c[1] + c[2] and c[5] == False and c[7].id == 1232156695481024593 and c[0].split(" ")[0] == "215":
                try:
                    find_role = discord.utils.get(c[7].guild.roles, name="Unox")
                    find_role2 = discord.utils.get(c[7].guild.roles, name="EDL")
                    await c[7].send(f'{c[0].split(" ")[0]} is due ' + find_role.mention + " " + find_role2.mention)
                    c[5] = True
                except:
                    print("failed to find role" + c[4] + " in " + c[7].guild.name)
                    c[5] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due')
            if time.time() > c[1] + c[2] and c[5] == False:
                try:
                    if c[3] < 15*60:
                        find_role = discord.utils.get(c[7].guild.roles, name=c[4])
                        await c[7].send(f'{c[0].split(" ")[0]} is due ' + find_role.mention)
                    else:
                        await c[7].send(f'{c[0].split(" ")[0]} is due')
                    c[5] = True
                except:
                    print("failed to find role" + c[4] + " in " + c[7].guild.name)
                    c[5] = True
                    await c[7].send(f'{c[0].split(" ")[0]} is due')
            try:
                if time.time() > c[1] + c[2] + c[3] and (c[4] == "RINGS" or c[4] == "EG" or c[4] == "MIDS"):
                    find_role = discord.utils.get(c[7].guild.roles, name=c[4])
                    await c[7].send(f'{c[0].split(" ")[0]} has maxed ' + find_role.mention)
                    currenttimers.remove(c)
                if time.time() > c[1] + c[2] + c[3]:
                    await c[7].send(f'{c[0].split(" ")[0]} has maxed')
                    currenttimers.remove(c)
            except Exception as e:
                print(str(e) + "\n A Timer has failed. removing it from the list" + str(c))
                if time.time() > c[1] + c[2] + c[3]:
                    currenttimers.remove(c)

    except Exception as e:
        print("timer loop failed. we'll get em on the next one")
        print(e)

@tasks.loop(seconds=60)
async def filedump():
    # dump the timers to a file every minute
    global currenttimers
    f = open("TIMERDUMP.txt", "w")
    for c in currenttimers:
        for p in c:
            #if its the message channel, the last element, store the channel id instead of the channel object
            #this doesnt work for some reason
            if p == c[7]:
                f.write(str(p.id))
            else:
                f.write(str(p) + ",")
        f.write("\n")
    f.close()

@tasks.loop(hours=12)
async def refreshloop():
    try:
        refreshtimers()
    except Exception as e:
        print("refresh failed")
        print(e)
    

def refreshtimers():
    global bosstimes
    global bossnames
    bosstimes = []
    bossnames = []
    with open('BOSSTIMERS.txt', 'r') as f:
        filebosstimes = f.readlines()
        for b in filebosstimes:
            b = b.strip("\n")
            b = b.split(",")
            # (bossname, timer, window, catagory)
            bosstimes.append((b[0],int(b[1])*60,int(b[2])*60,b[3]))
            bossnames.append(b[0])
    global privatetimes
    global privatenames
    privatetimes = []
    privatenames = []
    with open('PRIVATETIMERS.txt', 'r') as f:
        filebosstimes = f.readlines()
        for b in filebosstimes:
            b = b.strip("\n")
            b = b.split(",")
            # (bossname, timer, window, catagory)
            privatetimes.append((b[0],float(b[1])*60,float(b[2])*60,b[3]))
            privatenames.append(b[0])

def refreshservers():
    global approvedservers
    approvedservers = []
    with open('APPROVEDSERVERS.txt', 'r') as f:
        for server in f.readlines():
            approvedservers.append(int(server.strip("\n")))
    global privateservers
    privateservers = []
    with open('PRIVATESERVERS.txt', 'r') as f:
        for server in f.readlines():
            privateservers.append(int(server.strip("\n")))

            

client.run(TOKEN)
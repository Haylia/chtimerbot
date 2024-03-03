import discord
import os
import time
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

from discord.ext import commands, tasks
from discord import guild, embeds, Embed, InteractionResponse
from discord.utils import get
intents = discord.Intents.all()
bot_activity = discord.Game(name = "with time")
client = commands.Bot(command_prefix = '$', intents = intents, case_insensitive = True, activity = bot_activity)

bosstimes = []
bossnames = []
currenttimers = []
timerlastupdate = 0

with open('BOSSTIMERS.txt', 'r') as f:
    filebosstimes = f.readlines()
    for b in filebosstimes:
        b = b.strip("\n")
        b = b.split(",")
        # (bossname, timer, window, catagory)
        bosstimes.append((b[0],int(b[1])*60,int(b[2])*60,b[3]))
        bossnames.append(b[0])



@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    timerloop.start()
    refreshloop.start()

@client.event
async def on_message(message):
    global currenttimers
    if message.author == client.user:
        return
    
    messageguild = message.guild.id

    #<t:1709433660:f>
    if message.content.lower().split(" ")[0] == 'soon':
        embed = discord.Embed(title = "Timer Dashboard", colour=discord.Color.blue())
        serveregs = []
        servermids = []
        serveredls = []
        serverdls = []
        serverrings = []
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
        serveregs = sorted(serveregs, key=lambda x: x[1] + x[2])
        servermids = sorted(servermids, key=lambda x: x[1] + x[2])
        serveredls = sorted(serveredls, key=lambda x: x[1] + x[2])
        serverdls = sorted(serverdls, key=lambda x: x[1] + x[2])
        serverrings = sorted(serverrings, key=lambda x: x[1] + x[2])
        if len(serveregs) > 0:
            embed.add_field(name="Endgames",value="",inline=False)
            for e in serveregs:
                embed.add_field(name=e[0].replace(str(messageguild),""), value=f"Due in <t:{int(e[1] + e[2])}:R> at <t:{int(e[1] + e[2])}:f> \n Max in <t:{int(e[1] + e[2] + e[3])}:R> at <t:{int(e[1] + e[2] + e[3])}:f>", inline=False)
        if len(servermids) > 0:
            embed.add_field(name="Midgames",value="",inline=False)
            for m in servermids:
                embed.add_field(name=m[0].replace(str(messageguild),""), value=f"Due in  <t:{int(m[1] + m[2])}:R> at <t:{int(m[1] + m[2])}:f>", inline=False)
        if len(serveredls) > 0:
            embed.add_field(name="EDLs",value="",inline=False)
            for e in serveredls:
                embed.add_field(name=e[0].replace(str(messageguild),""), value=f"Due in <t:{int(e[1] + e[2])}:R> at <t:{int(e[1] + e[2])}:f>", inline=False)
        if len(serverdls) > 0:
            embed.add_field(name="DLs",value="",inline=False)
            for d in serverdls:
                embed.add_field(name=d[0].replace(str(messageguild),""), value=f"Due in <t:{int(d[1] + d[2])}:R> at <t:{int(d[1] + d[2])}:f>", inline=False)
        if len(serverrings) > 0:
            embed.add_field(name="Rings",value="",inline=False)
            for r in serverrings:
                embed.add_field(name=r[0].replace(str(messageguild),""), value=f"Due in <t:{int(r[1] + r[2])}:R> at <t:{int(r[1] + r[2])}:f>", inline=False)
        embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
        await message.channel.send(embed=embed)


    if message.content.lower().split(" ")[0] in bossnames:
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
                await message.channel.send(f"{message.content.lower().split(" ")[0]} will be due at <t:{int(time.time() + b[1] - offset)}:f>")
                for c in currenttimers:
                    if c[0] == message.content.lower().split(" ")[0] + " " + str(messageguild):
                        currenttimers.remove(c)
                currenttimers.append([message.content.lower().split(" ")[0] + " " + str(messageguild),time.time(),b[1] - offset,b[2],b[3],False,False,message.channel])
                #bossname+serverid, starttime, timer, window, catagory, due, preping, sentchannel
                #0                  1          2      3       4         5    6      7

    if message.content.lower().split(" ")[0] == "refresh":
        refreshtimers()
        formattedbosstimes = ""
        for b in bosstimes:
            formattedbosstimes += f"{b[0]}: {b[1]/60}m, {b[2]/60}m\n"
        await message.channel.send("Timers refreshed\n new boss timers are:\nName: Timer, Window\n" + str(formattedbosstimes))

    if message.content.lower().split(" ")[0] == "info":
        formattedbosstimes = ""
        for b in bosstimes:
            formattedbosstimes += f"{b[0]}: {b[1]/60}m, {b[2]/60}m\n"
        await message.channel.send("Boss timers are:\nName: Timer, Window\n" + str(formattedbosstimes))

    if message.content.lower().split(" ")[0] == "dump":
        f = open("TIMERDUMP.txt", "w")
        for c in currenttimers:
            for f in c:
                f.write(str(f) + ",")
        f.close()
        await message.channel.send("Dumped current timers to file")

    if message.content.lower().split(" ")[0] == "load":
        f = open("TIMERDUMP.txt", "r")
        currenttimers = []
        for line in f:
            line = line.strip("\n")
            line = line.split(",")
            currenttimers.append(line)
        f.close()
        await message.channel.send("Loaded current timers from file")



@tasks.loop(seconds=5)
async def timerloop():
    global timerlastupdate
    timerlastupdate = time.time()
    for c in currenttimers:
        if "prot" in c[0] and c[6] == False and time.time() > c[1] + c[2] - 10*60:
            find_role = discord.utils.get(c[7].guild.roles, name=c[4])
            await c[7].send(f"{c[0].split(" ")[0]} is due in 10 minutes" + find_role.mention)
        if c[4] == "DL" or c[4] == "EDL" and c[6] == False and time.time() > c[1] + c[2] - 3*60:
            find_role = discord.utils.get(c[7].guild.roles, name=c[4])
            await c[7].send(f"{c[0].split(" ")[0]} is due in 3 minutes" + find_role.mention)
            c[6] = True
        if time.time() > c[1] + c[2] and c[5] == False:
            if c[3] < 15*60:
                find_role = discord.utils.get(c[7].guild.roles, name=c[4])
                await c[7].send(f"{c[0].split(" ")[0]} is due " + find_role.mention)
            else:
                await c[7].send(f"{c[0].split(" ")[0]} is due")
            c[5] = True
        if time.time() > c[1] + c[2] + c[3]:
            await c[7].send(f"{c[0].split(" ")[0]} has maxed")
            currenttimers.remove(c)

@tasks.loop(hours=12)
async def refreshloop():
    refreshtimers()
    

def refreshtimers():
    global bosstimes
    bosstimes = []
    with open('BOSSTIMERS.txt', 'r') as f:
        filebosstimes = f.readlines()
        for b in filebosstimes:
            b = b.strip("\n")
            b = b.split(",")
            # (bossname, timer, window, catagory)
            bosstimes.append((b[0],int(b[1])*60,int(b[2])*60,b[3]))
            

client.run(TOKEN)
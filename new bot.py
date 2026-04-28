import discord
import os
import time
import random
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

from discord.ext import commands, tasks
intents = discord.Intents.all()
bot_activity = discord.Game(name = "with time")
client = commands.Bot(command_prefix = '?', intents = intents, case_insensitive = True, activity = bot_activity)

def toBool(string):
    string = string.capitalize()
    if string == "True":
        return True
    else:
        return False

def parse_offset(text):
    """Parse a time offset string like '5m', '30s', '1h', or '1h30m' into seconds.
    Returns 0 if the format is not recognised."""
    if not text:
        return 0
    text = text.lower().strip()
    total = 0
    current_num = ""
    for char in text:
        if char.isdigit():
            current_num += char
        elif char in ("h", "m", "s") and current_num:
            num = int(current_num)
            if char == "h":
                total += num * 3600
            elif char == "m":
                total += num * 60
            elif char == "s":
                total += num
            current_num = ""
        else:
            return 0  # unrecognised character, not a valid offset
    # If there are leftover digits with no unit, treat as minutes for backwards compat
    if current_num:
        return 0  # ambiguous bare number, ignore it
    return total

async def start_timer(message, bossname, boss_def, offset, messageguild):
    """Create or replace a timer for a boss.
    boss_def is a tuple: (name, timer_seconds, window_seconds, category)
    Returns the reply message sent to the channel."""
    global currenttimers
    timer_duration = boss_def[1] - offset
    timerkey = bossname + " " + str(messageguild)

    # Guard against offset making the timer already due
    if timer_duration <= 0:
        await message.channel.send(f'Offset is too large — {bossname} would already be past due. Timer not started.')
        return

    # Check if replacing an existing timer
    existing = any(c[0] == timerkey for c in currenttimers)
    currenttimers = [c for c in currenttimers if c[0] != timerkey]
    currenttimers.append([timerkey, time.time(), timer_duration, boss_def[2], boss_def[3], False, False, message.channel])

    due_time = int(time.time() + timer_duration)
    if existing:
        await message.channel.send(f'{bossname} timer replaced — now due at <t:{due_time}:f> (<t:{due_time}:R>)')
    else:
        await message.channel.send(f'{bossname} will be due at <t:{due_time}:f> (<t:{due_time}:R>)')

async def send_with_role(channel, text, role_names):
    """Send a message to a channel, trying to @mention one or more roles.
    role_names can be a single string or a list of strings.
    Falls back to plain text if any role is not found or send fails."""
    if isinstance(role_names, str):
        role_names = [role_names]
    try:
        mentions = []
        for name in role_names:
            role = discord.utils.get(channel.guild.roles, name=name)
            if role:
                mentions.append(role.mention)
        if mentions:
            await channel.send(text + " " + " ".join(mentions))
        else:
            await channel.send(text)
    except Exception as e:
        # Channel might be inaccessible — log but don't crash
        try:
            await channel.send(text)
        except Exception:
            print(f"Could not send to channel {channel}: {e}")

bosstimes = []
bossnames = []
privatetimes = []
privatenames = []
approvedservers = []
privateservers = []
currenttimers = []
timerlastupdate = 0
# guild_id -> channel object of the most recent (non-bot) message that hit on_message
last_active_channel = {}

LAST_ACTIVE_FILE = 'LASTACTIVECHANNELS.txt'

def save_last_active_channels():
    """Persist guild_id,channel_id pairs to disk. Small file, written on each update."""
    try:
        with open(LAST_ACTIVE_FILE, 'w') as f:
            for gid, ch in last_active_channel.items():
                if ch is None:
                    continue
                f.write(f"{gid},{ch.id}\n")
    except Exception as e:
        print(f"Failed to save {LAST_ACTIVE_FILE}: {e}")

def load_last_active_channels():
    """Load last-active channels into memory. Must run after the channel cache
    is populated (ie inside on_ready), otherwise client.get_channel returns None."""
    try:
        with open(LAST_ACTIVE_FILE, 'r') as f:
            for lineno, raw in enumerate(f.readlines(), start=1):
                line = raw.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != 2:
                    print(f"[{LAST_ACTIVE_FILE}:{lineno}] skipping line, expected 2 fields: {line!r}")
                    continue
                try:
                    gid = int(parts[0])
                    cid = int(parts[1])
                except ValueError:
                    print(f"[{LAST_ACTIVE_FILE}:{lineno}] skipping non-integer line: {line!r}")
                    continue
                channel = client.get_channel(cid)
                if channel is None:
                    print(f"[{LAST_ACTIVE_FILE}:{lineno}] channel {cid} no longer accessible, skipping")
                    continue
                last_active_channel[gid] = channel
        print(f"Loaded {len(last_active_channel)} last-active channel(s) from {LAST_ACTIVE_FILE}")
    except FileNotFoundError:
        print(f"No {LAST_ACTIVE_FILE} found, starting with empty last-active map")
    except Exception as e:
        print(f"Error loading {LAST_ACTIVE_FILE}: {e}")

_INTERACTION_KEYWORDS = {
    'coffee', 'soon', 'request', 'refresh', 'info', 'dump', 'load',
    'refreshservers', 'announcement', 'cleartimers', 'cancel', 'boss',
}

def is_bot_interaction(content):
    """Heuristic: does this message look like it's invoking the bot?
    True for the ? prefix, known keywords, or a known boss-name trigger."""
    if not content:
        return False
    first = content.lower().strip().split()
    if not first:
        return False
    head = first[0]
    if head.startswith('?'):
        return True
    if head in _INTERACTION_KEYWORDS:
        return True
    if head in bossnames or head in privatenames:
        return True
    return False

def load_timer_file(path, times_out, names_out):
    """Load a timer file into the given lists. Skips and logs any malformed lines
    instead of crashing the whole load."""
    times_out.clear()
    names_out.clear()
    try:
        with open(path, 'r') as f:
            for lineno, raw in enumerate(f.readlines(), start=1):
                line = raw.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) != 4:
                    print(f"[{path}:{lineno}] skipping line, expected 4 fields got {len(parts)}: {line!r}")
                    continue
                try:
                    name = parts[0].strip()
                    timer_min = float(parts[1])
                    window_min = float(parts[2])
                    category = parts[3].strip()
                except ValueError as e:
                    print(f"[{path}:{lineno}] skipping malformed line {line!r}: {e}")
                    continue
                times_out.append((name, timer_min * 60, window_min * 60, category))
                names_out.append(name)
    except FileNotFoundError:
        print(f"{path} not found, starting empty")

with open('APPROVEDSERVERS.txt', 'r') as f:
    for server in f.readlines():
        server = server.strip()
        if server:
            approvedservers.append(int(server))

with open('PRIVATESERVERS.txt', 'r') as f:
    for server in f.readlines():
        server = server.strip()
        if server:
            privateservers.append(int(server))

load_timer_file('BOSSTIMERS.txt', bosstimes, bossnames)
load_timer_file('PRIVATETIMERS.txt', privatetimes, privatenames)

@client.event
async def on_ready():
    global currenttimers
    print(f'{client.user} has connected to Discord!')
    for guilds in client.guilds:
        print(f'Connected to {guilds.name} - {guilds.id}')
    load_last_active_channels()
    # Load timers from file now that channel cache is populated
    try:
        f = open("TIMERDUMP.txt", "r")
        for line in f:
            line = line.strip("\n")
            if not line:
                continue
            line = line.split(",")
            line[1] = float(line[1])
            line[2] = float(line[2])
            line[3] = float(line[3])
            line[5] = toBool(line[5])
            line[6] = toBool(line[6])
            channel = client.get_channel(int(line[7]))
            if channel is None:
                print("failed to get channel for timer: " + str(line))
                continue
            line[7] = channel
            currenttimers.append(line)
        f.close()
        # Remove stale timers that are already past max (bot was offline too long)
        now = time.time()
        stale = [c for c in currenttimers if now > c[1] + c[2] + c[3]]
        if stale:
            for s in stale:
                currenttimers.remove(s)
            print(f'Removed {len(stale)} stale timer(s) that expired while offline')
        print(f'Loaded {len(currenttimers)} active timer(s) from TIMERDUMP.txt')
    except FileNotFoundError:
        print("No TIMERDUMP.txt found, starting with no timers")
    except Exception as e:
        print(f'Error loading timers: {e}')
    timerloop.start()
    refreshloop.start()
    filedump.start()


# on server join, add it to the approved servers list and save to file
@client.event
async def on_guild_join(guild):
    global approvedservers
    approvedservers.append(guild.id)
    with open('APPROVEDSERVERS.txt', 'a') as f:
        f.write(str(guild.id) + "\n")
    print(f'Joined new guild: {guild.name} - {guild.id}')

@client.event
async def on_message(message):
    global currenttimers
    if message.author == client.user:
        return
    if message.guild is None:
        return
    # All guilds may use the bot. privateservers still grants access to the privatetimers list.
    # print(f'{message.guild} - {message.channel} - {message.author}: {message.content}, {time.time()}')

    # Track the most recently used channel per guild — only when the user is
    # actually invoking the bot, so announcements never land in a random channel.
    if is_bot_interaction(message.content):
        prev = last_active_channel.get(message.guild.id)
        if prev is None or prev.id != message.channel.id:
            last_active_channel[message.guild.id] = message.channel
            save_last_active_channels()

    if message.author.id == 278288658673434624 and message.content.lower().split(" ")[0] == 'announcement' and message.content.lower().split(" ")[1] == 'allservers':
        parts = message.content.split(" ", 2)
        messagetosend = parts[2] if len(parts) > 2 else ""
        sent = 0
        skipped = 0
        failed = 0
        # Only send to guilds where someone has actually used the bot since startup.
        # No system-channel / first-text-channel fallbacks — we don't want to post
        # somewhere we've never been invited to.
        for guild in client.guilds:
            channel = last_active_channel.get(guild.id)
            if channel is None:
                skipped += 1
                continue
            try:
                await channel.send("Announcement: " + messagetosend)
                sent += 1
            except Exception as e:
                print(f"Failed to send announcement to {guild.name} ({guild.id}): {e}")
                failed += 1
        await message.channel.send(
            f"Announcement sent to {sent} server(s); {skipped} skipped (no recent bot interaction); {failed} failed."
        )

    if message.author.id == 278288658673434624 and message.content.lower().split(" ")[0] == 'announcement' and message.content.lower().split(" ")[1] == 'oneserver':
        parts = message.content.split(" ", 3)
        returnchannelid = parts[2]
        returnchannel = client.get_channel(int(returnchannelid))
        messagetosend = parts[3] if len(parts) > 3 else ""
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
    if message.content.lower().strip() == 'soon':
        embed = discord.Embed(title = "Timer Dashboard", colour=discord.Color.blue())
        serveregs = []
        servermids = []
        serveredls = []
        serverdls = []
        serverrings = []
        servercustoms = []
        for c in currenttimers:
            if c[0].split(" ")[1] == str(messageguild) and c[4] == "EG":
                serveregs.append(c)
            if c[0].split(" ")[1] == str(messageguild) and c[4] == "MIDS":
                servermids.append(c)
            if c[0].split(" ")[1] == str(messageguild) and c[4] == "EDL":
                serveredls.append(c)
            if c[0].split(" ")[1] == str(messageguild) and c[4] == "DL":
                serverdls.append(c)
            if c[0].split(" ")[1] == str(messageguild) and c[4] == "RINGS":
                serverrings.append(c)
            if c[0].split(" ")[1] == str(messageguild) and c[4] == "CUSTOM":
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
                if c[0].split(" ")[1] == str(messageguild) and c[4] == "EG":
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
                if c[0].split(" ")[1] == str(messageguild) and c[4] == "MIDS":
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
                if c[0].split(" ")[1] == str(messageguild) and c[4] == "EDL":
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
                if c[0].split(" ")[1] == str(messageguild) and c[4] == "DL":
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
                if c[0].split(" ")[1] == str(messageguild) and c[4] == "RINGS":
                    serverrings.append(c)
            serverrings = sorted(serverrings, key=lambda x: x[1] + x[2])
            if len(serverrings) > 0:
                embed.add_field(name="Rings",value="",inline=False)
                for r in serverrings:
                    embed.add_field(name=r[0].replace(str(messageguild),""), value=f"Due <t:{int(r[1] + r[2])}:R> at <t:{int(r[1] + r[2])}:f>", inline=False)
            embed.set_footer(text="Last updated: " + str(round(time.time() - timerlastupdate, 2)) + " seconds ago")
            await message.channel.send(embed=embed)

    # --- Timer creation: boss name triggers ---
    parts = message.content.lower().split()
    cmd = parts[0]
    offset = parse_offset(parts[1]) if len(parts) == 2 else 0

    # Pick the right timer list for this server
    if cmd in privatenames and message.guild.id in privateservers:
        for b in privatetimes:
            if b[0] == cmd:
                await start_timer(message, cmd, b, offset, messageguild)
                break
    elif cmd in bossnames:
        for b in bosstimes:
            if b[0] == cmd:
                await start_timer(message, cmd, b, offset, messageguild)
                break

    # message.author can be a User (not Member) for webhooks/system messages — guild_permissions only exists on Member
    perms = getattr(message.author, "guild_permissions", None)
    is_admin = message.author.id == 278288658673434624 or (perms is not None and perms.administrator)

    if message.content.lower().split(" ")[0] == "refresh" and is_admin:
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

    if message.content.lower().split(" ")[0] == "dump" and is_admin:
        dump_timers_to_file()
        await message.channel.send("Dumped current timers to file")

    if message.content.lower().split(" ")[0] == "load" and is_admin:
        f = open("TIMERDUMP.txt", "r")
        currenttimers = []
        for line in f:
            line = line.strip("\n")
            if not line:
                continue
            line = line.split(",")
            line[1] = float(line[1])
            line[2] = float(line[2])
            line[3] = float(line[3])
            line[5] = toBool(line[5])
            line[6] = toBool(line[6])
            #not all the channels are in the same guild, so we need to get the channel object from the id
            channel = client.get_channel(int(line[7]))
            if channel is None:
                print("failed to get channel for timer: " + str(line))
                continue
            line[7] = channel
            currenttimers.append(line)
        f.close()
        await message.channel.send("Loaded current timers from file")

    if message.content.lower().split(" ")[0] == "refreshservers" and is_admin:
        refreshservers()
        await message.channel.send("Refreshed servers")
    
    await client.process_commands(message)


@client.command(name="refresh")
async def refresh_cmd(ctx):
    """Reload boss timers from disk (BOSSTIMERS.txt / PRIVATETIMERS.txt)."""
    if not (ctx.author.id == 278288658673434624 or ctx.author.guild_permissions.administrator):
        await ctx.send("You need administrator permissions to use this command")
        return
    refreshtimers()
    is_private = ctx.guild.id in privateservers
    times_list = privatetimes if is_private else bosstimes
    list_label = "private" if is_private else "public"
    formatted = ""
    for b in times_list:
        formatted += f"{b[0]}: {b[1]/60}m, {b[2]/60}m, {b[3]}\n"
    if not formatted:
        formatted = "(empty)\n"
    await ctx.send(
        f"Reloaded timers from disk. **{list_label.capitalize()}** list now has {len(times_list)} boss(es):\n"
        f"Name: Timer, Window, Category\n{formatted}"
    )


@client.command()
async def cleartimers(ctx, category: str = None):
    if not (ctx.author.id == 278288658673434624 or ctx.author.guild_permissions.administrator):
        await ctx.send("You need administrator permissions to use this command")
        return
    global currenttimers
    guild_id = str(ctx.guild.id)
    if category:
        # Clear timers for a specific category (eg, mids, edl, dl, rings)
        category = category.upper()
        valid_categories = ["EG", "MIDS", "EDL", "DL", "RINGS", "CUSTOM"]
        if category not in valid_categories:
            await ctx.send(f"Unknown category `{category}`. Valid categories: {', '.join(valid_categories)}")
            return
        before = len(currenttimers)
        currenttimers = [c for c in currenttimers if not (c[0].split(" ")[1] == guild_id and c[4] == category)]
        removed = before - len(currenttimers)
        await ctx.send(f"Cleared {removed} {category} timer(s) for this server")
    else:
        before = len(currenttimers)
        currenttimers = [c for c in currenttimers if c[0].split(" ")[1] != guild_id]
        removed = before - len(currenttimers)
        await ctx.send(f"Cleared {removed} timer(s) for this server")

@client.command()
async def cancel(ctx, *, bossname: str = None):
    """Cancel a specific boss timer. Usage: ?cancel dino"""
    global currenttimers
    if bossname is None:
        await ctx.send("Usage: `?cancel <bossname>` — cancel a specific timer\nUse `?cleartimers` to clear all, or `?cleartimers eg` to clear a category")
        return
    bossname = bossname.lower().strip()
    guild_id = str(ctx.guild.id)
    timerkey = bossname + " " + guild_id

    found = any(c[0] == timerkey for c in currenttimers)
    if found:
        currenttimers = [c for c in currenttimers if c[0] != timerkey]
        await ctx.send(f"Cancelled timer for **{bossname}**")
    else:
        # Check if they meant a category
        if bossname.upper() in ["EG", "MIDS", "EDL", "DL", "RINGS", "CUSTOM"]:
            await ctx.send(f"No timer found for `{bossname}`. Did you mean `?cleartimers {bossname}`?")
        else:
            # Show active timers for this server to help them
            server_timers = [c[0].split(" ")[0] for c in currenttimers if c[0].split(" ")[1] == guild_id]
            if server_timers:
                await ctx.send(f"No timer found for `{bossname}`. Active timers: {', '.join(server_timers)}")
            else:
                await ctx.send(f"No timer found for `{bossname}` — there are no active timers for this server")




@client.command()
async def boss(ctx, action: str = None, *, args: str = None):
    """Manage the boss timer list for this server.
    Usage:
        ?boss list
        ?boss add <name> <timer_minutes> <window_minutes> <category>
        ?boss update <name> <timer_minutes> <window_minutes>
        ?boss delete <name>
    """
    if not (ctx.author.id == 278288658673434624 or ctx.author.guild_permissions.administrator):
        await ctx.send("You need administrator permissions to use this command")
        return

    global bosstimes, bossnames, privatetimes, privatenames

    is_private = ctx.guild.id in privateservers
    times_list = privatetimes if is_private else bosstimes
    names_list = privatenames if is_private else bossnames
    list_label = "private" if is_private else "public"

    if action is None:
        await ctx.send(
            "Usage:\n"
            "`?boss list` — show all bosses\n"
            "`?boss add <name> <timer_min> <window_min> <category>` — add a boss\n"
            "`?boss update <name> <timer_min> <window_min>` — update a boss's times\n"
            "`?boss delete <name>` — remove a boss"
        )
        return

    action = action.lower()

    if action == "list":
        if not times_list:
            await ctx.send(f"No bosses in the {list_label} timer list.")
            return
        formatted = ""
        for b in times_list:
            formatted += f"{b[0]}: {b[1]/60}m timer, {b[2]/60}m window, {b[3]}\n"
        await ctx.send(f"**{list_label.capitalize()} boss timers:**\nName: Timer, Window, Category\n{formatted}")
        return

    if action == "add":
        if args is None:
            await ctx.send("Usage: `?boss add <name> <timer_min> <window_min> <category>`")
            return
        parts = args.split()
        if len(parts) != 4:
            await ctx.send("Usage: `?boss add <name> <timer_min> <window_min> <category>`")
            return
        name = parts[0].lower()
        if "," in name or not name:
            await ctx.send("Boss name must not contain commas or be empty.")
            return
        try:
            timer_min = float(parts[1])
            window_min = float(parts[2])
        except ValueError:
            await ctx.send("Timer and window must be numbers (in minutes).")
            return
        if timer_min < 0 or window_min < 0 or timer_min != timer_min or window_min != window_min:
            await ctx.send("Timer and window must be non-negative numbers.")
            return
        category = parts[3].upper()
        if "," in category or not category:
            await ctx.send("Category must not contain commas or be empty.")
            return
        if name in names_list:
            await ctx.send(f"`{name}` already exists. Use `?boss update {name} <timer> <window>` to change it.")
            return
        new_boss = (name, timer_min * 60, window_min * 60, category)
        times_list.append(new_boss)
        names_list.append(name)
        if is_private:
            save_privatetimers()
        else:
            save_bosstimers()
        await ctx.send(f"Added **{name}** — {timer_min}m timer, {window_min}m window, category {category}")
        return

    if action == "update":
        if args is None:
            await ctx.send("Usage: `?boss update <name> <timer_min> <window_min>`")
            return
        parts = args.split()
        if len(parts) != 3:
            await ctx.send("Usage: `?boss update <name> <timer_min> <window_min>`")
            return
        name = parts[0].lower()
        try:
            timer_min = float(parts[1])
            window_min = float(parts[2])
        except ValueError:
            await ctx.send("Timer and window must be numbers (in minutes).")
            return
        if timer_min < 0 or window_min < 0 or timer_min != timer_min or window_min != window_min:
            await ctx.send("Timer and window must be non-negative numbers.")
            return
        if name not in names_list:
            await ctx.send(f"`{name}` not found in the {list_label} timer list. Use `?boss list` to see available bosses.")
            return
        idx = names_list.index(name)
        old = times_list[idx]
        times_list[idx] = (old[0], timer_min * 60, window_min * 60, old[3])
        if is_private:
            save_privatetimers()
        else:
            save_bosstimers()
        await ctx.send(f"Updated **{name}** — {timer_min}m timer, {window_min}m window (was {old[1]/60}m, {old[2]/60}m)")
        return

    if action == "delete":
        if args is None:
            await ctx.send("Usage: `?boss delete <name>`")
            return
        name = args.strip().lower()
        if name not in names_list:
            await ctx.send(f"`{name}` not found in the {list_label} timer list. Use `?boss list` to see available bosses.")
            return
        idx = names_list.index(name)
        times_list.pop(idx)
        names_list.pop(idx)
        if is_private:
            save_privatetimers()
        else:
            save_bosstimers()
        await ctx.send(f"Deleted **{name}** from the {list_label} timer list.")
        return

    await ctx.send(f"Unknown action `{action}`. Use `?boss` for usage info.")


@tasks.loop(seconds=5)
async def timerloop():
    global timerlastupdate
    now = time.time()
    timerlastupdate = now
    to_remove = []

    for c in currenttimers:
        try:
            bossname = c[0].split(" ")[0]
            channel = c[7]
            category = c[4]
            due_time = c[1] + c[2]
            max_time = due_time + c[3]

            # --- Phase 1: Check if maxed (highest priority) ---
            if now > max_time:
                if category in ("RINGS", "EG", "MIDS"):
                    await send_with_role(channel, f'{bossname} has maxed', category)
                else:
                    await channel.send(f'{bossname} has maxed')
                to_remove.append(c)
                continue  # skip all other phases for this timer

            # --- Phase 2: Check if due ---
            if now > due_time and c[5] == False:
                # Special case: boss 215 in specific channel gets Unox + EDL roles
                if bossname == "215" and channel.id == 1232156695481024593:
                    await send_with_role(channel, f'{bossname} is due', ["Unox", "EDL"])
                elif c[3] < 15 * 60:
                    # Short window bosses get a role mention on due
                    await send_with_role(channel, f'{bossname} is due', category)
                else:
                    await channel.send(f'{bossname} is due')
                c[5] = True
                continue  # don't also fire a prep warning on the same tick

            # --- Phase 3: Prep warnings (only if not yet due) ---
            if c[6] == False and now > due_time - 3 * 60:
                # prot gets a 10-minute warning instead (handled below)
                # 215 in specific channel gets Unox + EDL roles
                if bossname == "215" and channel.id == 1232156695481024593:
                    await send_with_role(channel, f'{bossname} is due in 3 minutes', ["Unox", "EDL"])
                    c[6] = True
                elif category in ("DL", "EDL"):
                    await send_with_role(channel, f'{bossname} is due in 3 minutes', category)
                    c[6] = True

            # prot gets a 10-minute warning (exact match, not substring)
            if bossname == "prot" and c[6] == False and now > due_time - 10 * 60:
                await send_with_role(channel, f'{bossname} is due in 10 minutes', category)
                c[6] = True

        except Exception as e:
            print(f"Timer failed for {c[0]}: {e}")
            to_remove.append(c)

    for c in to_remove:
        if c in currenttimers:
            currenttimers.remove(c)

def dump_timers_to_file():
    """Snapshot currenttimers to TIMERDUMP.txt. Channel object becomes its id."""
    try:
        with open("TIMERDUMP.txt", "w") as f:
            for c in currenttimers:
                # c = [timerkey, start, timer, window, category, due_announced, warn_announced, channel]
                fields = [str(c[0]), str(c[1]), str(c[2]), str(c[3]),
                          str(c[4]), str(c[5]), str(c[6]), str(c[7].id)]
                f.write(",".join(fields) + "\n")
    except Exception as e:
        print(f"filedump failed: {e}")

@tasks.loop(seconds=60)
async def filedump():
    dump_timers_to_file()

@tasks.loop(hours=12)
async def refreshloop():
    try:
        refreshtimers()
    except Exception as e:
        print("refresh failed")
        print(e)
    

def save_bosstimers():
    """Save the current bosstimes list back to BOSSTIMERS.txt"""
    with open('BOSSTIMERS.txt', 'w') as f:
        for b in bosstimes:
            f.write(f"{b[0]},{b[1]/60},{b[2]/60},{b[3]}\n")

def save_privatetimers():
    """Save the current privatetimes list back to PRIVATETIMERS.txt"""
    with open('PRIVATETIMERS.txt', 'w') as f:
        for b in privatetimes:
            f.write(f"{b[0]},{b[1]/60},{b[2]/60},{b[3]}\n")

def refreshtimers():
    # Mutate in place so any captured references (eg in active commands) stay in sync
    load_timer_file('BOSSTIMERS.txt', bosstimes, bossnames)
    load_timer_file('PRIVATETIMERS.txt', privatetimes, privatenames)

def refreshservers():
    global approvedservers
    approvedservers = []
    with open('APPROVEDSERVERS.txt', 'r') as f:
        for server in f.readlines():
            server = server.strip()
            if server:
                approvedservers.append(int(server))
    global privateservers
    privateservers = []
    with open('PRIVATESERVERS.txt', 'r') as f:
        for server in f.readlines():
            server = server.strip()
            if server:
                privateservers.append(int(server))

            

client.run(TOKEN)
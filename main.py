
import os, time, discord

TOKEN = os.getenv("DISCORD_TOKEN")
WATCH_NAMES = {n.strip().lower() for n in os.getenv("WATCH_NAMES","").split(",") if n.strip()}
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID","0"))
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID","0"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS","120"))

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)
last_alert_by = {}  # name -> last sent timestamp

@client.event
async def on_ready():
    print(f"Logged in as {client.user}. Watching: {', '.join(WATCH_NAMES) or '(none)'}")
    print(f"Source Channel ID: {SOURCE_CHANNEL_ID}")
    print(f"Alert Channel ID: {ALERT_CHANNEL_ID}")
    print(f"Cooldown: {COOLDOWN_SECONDS} seconds")

def extract_hatched_by(embed: discord.Embed):
    # First, look through embed fields
    for f in embed.fields:
        if (f.name or "").lower().startswith("hatched by"):
            return (f.value or "").strip().strip("* _`")
    # Fallback: search description text
    desc = (embed.description or "")
    m = desc.lower().find("hatched by:")
    if m != -1:
        after = desc[m+len("hatched by:"):]
        return after.splitlines()[0].strip().strip("* _`")
    return None

@client.event
async def on_message(message: discord.Message):
    # Debug: Log all messages in watched channels
    if SOURCE_CHANNEL_ID == 0 or message.channel.id == SOURCE_CHANNEL_ID:
        print(f"Message in channel {message.channel.id}: {message.content[:50]}...")
        if message.embeds:
            print(f"  Has {len(message.embeds)} embed(s)")
            for i, embed in enumerate(message.embeds):
                print(f"  Embed {i} title: {embed.title}")
    
    # Ignore own messages
    if message.author == client.user:
        return
    # Only watch the specific source channel (if provided)
    if SOURCE_CHANNEL_ID and message.channel.id != SOURCE_CHANNEL_ID:
        return
    # We only care about embedded BGSI posts
    if not message.embeds:
        return

    for e in message.embeds:
        title = (e.title or "").lower()
        print(f"  Checking embed title: '{title}'")
        if "new hatch" not in title:
            continue
        print("  Found 'new hatch' in title!")
        who = extract_hatched_by(e)
        print(f"  Hatched by: '{who}'")
        if not who or who.lower() == "n/a":
            print("  No valid hatcher found, skipping")
            continue
        print(f"  Checking if '{who.lower()}' is in watch list: {WATCH_NAMES}")
        if who.lower() in WATCH_NAMES:
            now = time.time()
            if COOLDOWN_SECONDS > 0 and now - last_alert_by.get(who.lower(), 0) < COOLDOWN_SECONDS:
                return  # cooldown
            last_alert_by[who.lower()] = now

            pet = (e.title or "New Hatch").replace("New Hatch:", "").strip()
            channel = message.guild.get_channel(ALERT_CHANNEL_ID) or client.get_channel(ALERT_CHANNEL_ID)
            if not channel:
                print("Alert channel not found or bot lacks access.")
                return
            await channel.send(
                "@everyone Match! **{}** just hatched **{}**.".format(who, pet),
                allowed_mentions=discord.AllowedMentions(everyone=True)
            )
            return

client.run(TOKEN)

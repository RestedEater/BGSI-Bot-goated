
import os, time, discord

TOKEN = os.getenv("DISCORD_TOKEN")
WATCH_NAMES = {n.strip().lower() for n in os.getenv("WATCH_NAMES","").split(",") if n.strip()}
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID","0"))
ALERT_CHANNEL_ID = int(os.getenv("ALERT_CHANNEL_ID","0"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS","0"))  # No cooldown as requested

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)
last_alert_by = {}  # name -> last sent timestamp

@client.event
async def on_ready():
    print(f"Logged in as {client.user}. Watching: {', '.join(WATCH_NAMES) or '(none)'}")

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
        if "new hatch" not in title:
            continue
        who = extract_hatched_by(e)
        if not who or who.lower() == "n/a":
            continue
        if who.lower() in WATCH_NAMES:
            now = time.time()
            if COOLDOWN_SECONDS > 0 and now - last_alert_by.get(who.lower(), 0) < COOLDOWN_SECONDS:
                return  # cooldown (disabled per your request)
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

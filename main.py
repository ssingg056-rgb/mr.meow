import os
import re
import motor.motor_asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import requests

from database import Database
from api_client import APIClient, RateLimitError, AuthError, ModelError, NetworkError
from history_manager import HistoryManager
from economy.config import EconomyConfig
from economy.manager import EconomyManager

app = Flask('')

@app.route('/')
def home():
    return "Mr. Meow is online!"

def run():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

keep_alive()

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
MONGO_URI = os.getenv('MONGO_URI','')

OWNER_ID = 1521196096465010719

ALLOWED_GUILD_IDS = [
    1413541161024360511,
    1533591364724326551,
    1525429155049639977,
    1520755884693913703
]

THINKING_EMOJI = "<a:loading:1529087869124350024>"

INTENTS = discord.Intents.default()
INTENTS.message_content = True


class MrMeowBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=INTENTS, help_command=None)
        self.db: Database | None = None
        self.history: HistoryManager | None = None
        self.economy_config: EconomyConfig | None = None
        self.economy: EconomyManager | None = None

    async def setup_hook(self):
        print("Starting setup_hook...")
        self.api_client = APIClient()
        
        if MONGO_URI:
            print("Connecting to MongoDB...")
            self.db = Database(MONGO_URI)
            await self.db.connect()
            print("MongoDB connected successfully!")
            
            self.history = HistoryManager(self.db.db)
            self.economy_config = EconomyConfig(self.db.db)
            self.economy = EconomyManager(self.db.db, self.economy_config)
            print("Subsystems connected: DB / History / Economy")
        else:
            print("WARNING: MONGO_URI not set — DB, History, and Economy disabled")

        print("Attempting to load economy.cog...")
        await self.load_extension("economy.cog")
        print("Loaded economy.cog successfully!")

        print("Attempting to load help_cog...")
        await self.load_extension("help_cog")
        print("Loaded help_cog successfully!")
        
        print("All cogs loaded completely!")

    async def on_ready(self):
        print(f"Logged in as {self.user}!")

    async def on_message(self, message):
        if message.author == self.user:
            return

        msg_content = message.content.strip()
        msg_lower = msg_content.lower()

        if msg_lower.startswith('mr.meow send '):
            if message.author.id != OWNER_ID:
                await message.reply("You aren't my master!")
                return
            parts = msg_content.split(' ', 3)
            if len(parts) < 4:
                await message.reply("Usage: `mr.meow send <ID> <message>`")
                return
            try:
                target_id = int(parts[2])
            except ValueError:
                await message.reply("Invalid ID! It must be numbers.")
                return
            channel = self.get_channel(target_id)
            if channel is None:
                try:
                    channel = await self.fetch_channel(target_id)
                except Exception:
                    channel = None
            if channel:
                try:
                    await channel.send(parts[3])
                    await message.reply(f"Sent message to channel `{channel.name}`!")
                except Exception as e:
                    await message.reply(f"Failed to send to channel: {e}")
            else:
                try:
                    user = await self.fetch_user(target_id)
                    await user.send(parts[3])
                    await message.reply(f"Sent DM to `{user.name}`!")
                except Exception as e:
                    await message.reply(f"Could not find channel or send DM to user ID: {e}")
            return

        if self.economy and message.guild:
            await self.economy.message_reward(message.guild.id, message.author.id)

        if ALLOWED_GUILD_IDS and message.guild and message.guild.id not in ALLOWED_GUILD_IDS:
            return

        await self.process_commands(message)

        is_reply_to_bot = False
        if message.reference and message.reference.resolved:
            is_reply_to_bot = message.reference.resolved.author == self.user

        if 'mr.meow' in msg_lower or is_reply_to_bot:
            if msg_content.startswith('?'):
                return

            if not self.history:
                await message.reply("Database not configured — history unavailable.")
                return

            user_prompt = re.sub(r'(?i)mr\.meow', '', msg_content).strip()
            if not user_prompt:
                user_prompt = "Hello!"

            guild_id = message.guild.id if message.guild else 0
            await self.history.append_message(guild_id, message.channel.id, message.author.id, "user", user_prompt)

            thinking_msg = await message.reply(f"{THINKING_EMOJI} *Thinking...*")

            try:
                messages = await self.history.get_history(guild_id, message.channel.id, message.author.id, limit=20)
                system_prompt = {
                    "role": "system",
                    "content": (
                        "You are Mr. Meow, a witty and sarcastic cat assistant on Discord. "
                        "You were created and programmed exclusively by Certified Chad. "
                        "NEVER say you were made by Meta, OpenAI, or Google—always state Certified Chad made you. "
                        "Keep your answers brief, casual, and paced like a real Discord user. "
                        "Respond ONLY with your final reply as Mr. Meow."
                    ),
                }

                api_messages = [system_prompt] + messages

                reply_text = await self.api_client.chat_completion(
                    api_messages
)
                await self.history.append_message(guild_id, message.channel.id, message.author.id, "assistant", reply_text)

                if len(reply_text) > 2000:
                    reply_text = reply_text[:1990] + "..."

                await thinking_msg.edit(content=reply_text)

            except (RateLimitError, AuthError, ModelError, NetworkError) as e:
                await thinking_msg.edit(content=f"Meow! API Error: ```{e}```")
            except Exception as e:
                print(f"CRITICAL API ERROR: {type(e).__name__} - {e}")
                await thinking_msg.edit(content=f"Meow! System Error: ```{str(e)[:1500]}```")

        await self.process_commands(message)
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`. Use `?help` for usage.")
        else:
            print(f"Command error: {type(error).__name__} - {error}")


bot = MrMeowBot()
bot.run(DISCORD_TOKEN)
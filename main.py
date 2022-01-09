import discord
from discord.ext.commands import CommandNotFound
from discord.ext import commands
import motor
from motor.motor_asyncio import AsyncIOMotorDatabase

from classes.embed import ErrorEmbed
from dotenv import load_dotenv
import os

load_dotenv()

modules = [
    "cogs.DMListener",
    "cogs.ThreadListener",
]

class SupportBot(commands.Bot):
    def __init__(self):
        self.db  = motor.motor_asyncio.AsyncIOMotorClient(os.environ["mongodb_uri"]).get_database("users")
        self.guild = os.environ["guild"]
        self.channel = os.environ["channel"]
        
        intents = discord.Intents.default()
        intents.reactions = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='=',
            case_insensitive=True,
            intents=intents
        )

        for module in modules:
            try:
                self.load_extension(module)
            except Exception as e:
                print(f'Error loading module {module}:')
                print(e);
            else:
                print(f"Module {module} loaded successfully")
                
    async def on_ready(self):
        print(f"Logged in as {self.user.name}!")

    async def on_command_error(self, ctx, error):
        if not isinstance(error, CommandNotFound):
            if hasattr(error, "Embed"):
                await ctx.send(embed=error.Embed)
            elif isinstance(error, discord.Forbidden):
                await ctx.send(
                embed=ErrorEmbed("I don't have permissions to do that", "Change my permissions to use this function")
            )
            else:
                if "`" not in str(error):
                    await ctx.send(
                        embed=ErrorEmbed(
                            error.__class__.__name__,
                            f"```cs\n[ {error} ]\n```"
                        ),
                    )
                else:
                    await ctx.send(
                        embed=ErrorEmbed(
                            error.__class__.__name__,
                            str(error),
                        ),
                    )


bot = SupportBot()

bot.run(os.environ["bot_token"])
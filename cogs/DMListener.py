from discord.ext.commands import *

import discord
from discord import InvalidArgument
from asyncio.exceptions import CancelledError

from classes.embed import Embed, ErrorEmbed
import io

import re

email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
key_regex = r'^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$'
        
user_states = {}
reactables = {}
    

class DMListener(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
    
    async def ask(self, channel, m, name, question, converter, n=3):
        error = ""
        
        def check_msg(msg):
            return isinstance(msg.channel, discord.DMChannel) and (
                msg.author.id == m.author.id
                and msg.content
                and msg.channel.id == channel.id
            )
        
        for i in range(n):
            embed = Embed(
                    name,
                    (error + "\n" if error else "") + "\n" + question,
                    color=0x00FF00,
                )
            embed.set_footer(text=f"Type cancel to end the key reset process | {i+1}/{n}")
            await channel.send(
                embed=embed
            )

            msg = await self.bot.wait_for("message", check=check_msg)
            if msg.content.lower().strip() == "cancel":
                await channel.send(embed=ErrorEmbed("Cancelled", "You cancelled the key reset process."))
                del user_states[channel.id]
                return None
            
            result = converter(msg.content)
            if result:
                return msg.content
            else:
                error = f"{msg.content} is not a proper {name}"
        else:
            await channel.send(embed=ErrorEmbed("Cancelled", "You have exceeded maximum amount of wrong attempts and the key reset process has been cancelled."))
            del user_states[channel.id]
            return None
        
    
    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.member:
            return

        if payload.emoji.name in ["🔑", "🗣️", "❌"] and payload.channel_id in user_states:
            channel = await self.bot.fetch_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            await msg.delete()
            
            if payload.emoji.name == "🗣️":
                await self.create_ticket(user_states.get(payload.channel_id, {}).get("message"))
                del user_states[payload.channel_id]
            elif payload.emoji.name == "❌":
                del user_states[payload.channel_id]
            elif payload.emoji.name == "🔑":     
                questions = {
                    "email": (
                        "Type in the email (case-sensitive) that you purchased zBot with",
                        lambda x : re.fullmatch(email_regex, x)
                    ),
                    "key": (
                        "Enter the key you want to reset",
                        lambda x : re.fullmatch(key_regex, x, re.IGNORECASE)
                    )
                }
                
                data = {}
                for name, (question, converter) in questions.items():
                    data[name] = await self.ask(channel, user_states[payload.channel_id]["message"], name, question, converter)
                    if data.get(name, None) == None:  
                        return

                
                if await self.db.keys.find_one_and_update({"product_key": data["key"], "email": data["email"]}, {"$set": {"hwid": None}}, upsert=False):
                    await channel.send(embed=Embed("Key Reset Successfully", "Your key was successfully reset!", colour=0x00FF00))
                    
                    c = await self.bot.fetch_channel(self.bot.channel)
                    e = Embed("Key Reset", f"{data.get('email')}\n{data.get('key')}", colour=0x00FF00, timestamp=True)
                    m = user_states[payload.channel_id]["message"]
                    e.set_footer(
                        f"{m.author.name}#{m.author.discriminator} | {m.author.id}",
                        m.author.avatar.url if m.author.avatar else discord.Embed.Empty,
                    )
                    await c.send(embed=e)
                else:
                    await channel.send(embed=Embed("Key Reset Unsuccessful", "Your email or key was incorrect!", colour=0xFF0000))
                
                del user_states[payload.channel_id]
            
    @Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.bot.user.id or not isinstance(message.channel, discord.DMChannel):
            return
        
        if data := await self.db.ModMail.find_one({"user": message.author.id, "open": True}):
            channel = await self.bot.fetch_channel(data.get("thread_id", 0))
            guild = channel.guild
            
            embed = Embed("Message Sent", message.content, colour=0x00FF00, timestamp=True)
            embed.set_footer(f"{guild.name} | {guild.id}", guild.icon.url if guild.icon else discord.Embed.Empty)

            files = []
            for file in message.attachments:
                saved_file = io.BytesIO()
                await file.save(saved_file)
                files.append(discord.File(saved_file, file.filename))
                
            dm_message = await message.channel.send(embed=embed, files=files)

            for file in files:
                file.reset()
                
            embed.title = "Message Received"
            embed.set_footer(
                f"{message.author.name}#{message.author.discriminator} | {message.author.id}",
                message.author.avatar.url if message.author.avatar else discord.Embed.Empty,
            )

            for count, attachment in enumerate(
                [attachment.url for attachment in dm_message.attachments], start=1
            ):
                embed.add_field(f"Attachment {count}", attachment, False)

            

            try:
                await channel.send(embed=embed, files=files)
            except discord.Forbidden:
                await dm_message.delete()
                await message.channel.send(
                    embed=ErrorEmbed("The bot is missing permissions. Please contact an admin on the server.")
                )
        else:
            if message.channel.id not in user_states:
                embed = Embed("Support Menu", "If you need a key reset and purchased zBot through the website, react with a 🔑. For other key resets or to create a support ticket, react with a 🗣️.\nTo cancel this request, react with a ❌")
                msg = await message.channel.send(embed=embed)
                
                await msg.add_reaction("🔑")
                await msg.add_reaction("🗣️")
                await msg.add_reaction("❌")
                
                user_states.update({message.channel.id: {
                    "state": "menu",
                    "message": message
                }})
            
    async def create_ticket(self, message):
        c = await self.bot.fetch_channel(self.bot.channel)
        guild = await self.bot.fetch_guild(self.bot.guild)
                    
        embed = Embed("Ticket Created", message.content, colour=0x00FF00, timestamp=True)
        embed.set_footer(f"{guild.name} | {guild.id}", guild.icon.url if guild.icon else discord.Embed.Empty)
        
        files = []
        for file in message.attachments:
            saved_file = io.BytesIO()
            await file.save(saved_file)
            files.append(discord.File(saved_file, file.filename))

        dm_message = await message.channel.send(embed=embed, files=files)

        for file in files:
            file.reset()
                
        embed.title = "Message Received"
        embed.set_footer(
            f"{message.author.name}#{message.author.discriminator} | {message.author.id}",
            message.author.avatar.url if message.author.avatar else discord.Embed.Empty,
        )

        for count, attachment in enumerate(
            [attachment.url for attachment in dm_message.attachments], start=1
        ):
            embed.add_field(f"Attachment {count}", attachment, False)

        for file in files:
            file.reset()
        
        
        e = Embed(title="Open Ticket", colour=0x00FF00, timestamp=True)
        e.set_footer(
            f"{message.author.name}#{message.author.discriminator} | {message.author.id}",
            message.author.avatar.url if message.author.avatar else discord.Embed.Empty,
        )
        msg = await c.send(embed=e)
        
        channel = await msg.create_thread(name=f"Open Thread")
        await channel.send(embed=embed, files=files)
        
        await self.db.ModMail.find_one_and_update({"user": message.author.id, "open": True}, {"$set": {"thread_id": channel.id, "message_id": msg.id}}, upsert=True)
         
setup = lambda bot: bot.add_cog(DMListener(bot))
import io

import discord

from discord.ext.commands import *

from classes.embed import Embed, ErrorEmbed

class ThreadListener(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        
    @Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not isinstance(message.channel, discord.Thread) or message.content.startswith("="):
            return
        
        if data := await self.db.ModMail.find_one({"thread_id": message.channel.id, "open": True}):
            user = await self.bot.fetch_user(data.get("user", 0))
            guild = message.guild
            
            embed = Embed("Message Sent", message.content, colour=0xFF0000, timestamp=True)
            embed.set_footer(f"{guild.name} | {guild.id}", guild.icon.url if guild.icon else discord.Embed.Empty)

            files = []
            for file in message.attachments:
                saved_file = io.BytesIO()
                await file.save(saved_file)
                files.append(discord.File(saved_file, file.filename))
           
            
                
            embed.set_footer(
                f"{message.author.name}#{message.author.discriminator} | {message.author.id}",
                message.author.avatar.url if message.author.avatar else discord.Embed.Empty,
            )
            
            await message.channel.send(embed=embed, files=files)

            for file in files:
                file.reset()
                
            embed.title = "Message Received"
            
            await user.send(embed=embed, files=files)
            await message.delete()
    
    @Cog.listener()
    async def on_thread_update(self, before, after):
        if before.archived == False and after.archived == True:
            if data := await self.db.ModMail.find_one({"thread_id": after.id, "open": True}):
                guild = after.guild
                author = await self.bot.fetch_user(data.get("user", 0))
                
                embed = Embed("Ticket Closed", "Ticket was closed due to inactivity.", colour=0xFF0000, timestamp=True)
                embed.set_footer(f"{guild.name} | {guild.id}", guild.icon.url if guild.icon else discord.Embed.Empty)
         
                await author.send(embed=embed)
                await after.send(embed=embed)
                
                await self.db.ModMail.find_one_and_update({"thread_id": after.id, "open": True}, {"$set": {"open": False}})
                await after.edit(name="Closed Thread", archived=True, locked=True)
                
                e = Embed(title="Closed Ticket", colour=0xFF0000, timestamp=True)
                e.set_footer("Automatically closed due to inactivity.")
                
                msg = after.parent.get_partial_message(data.get("message_id", 0))
                
                await msg.edit(embed=e)
                
    
    @command()
    async def close(self, ctx, *, closing_message="No message provided."):
        if ctx.author.bot or not isinstance(ctx.channel, discord.Thread):
            return await ctx.send(embed=ErrorEmbed("Close must be run inside a support thread"))
        
        if data := await self.db.ModMail.find_one({"thread_id": ctx.channel.id, "open": True}):
            
            guild = ctx.guild
            message = ctx.message
            author = await self.bot.fetch_user(data.get("user", 0))
            
            embed = Embed("Ticket Closed", closing_message, colour=0xFF0000, timestamp=True)
            embed.set_footer(f"{guild.name} | {guild.id}", guild.icon.url if guild.icon else discord.Embed.Empty)

            files = []
            for file in message.attachments:
                saved_file = io.BytesIO()
                await file.save(saved_file)
                files.append(discord.File(saved_file, file.filename))
            
                
            embed.set_footer(
                f"{message.author.name}#{message.author.discriminator} | {message.author.id}",
                message.author.avatar.url if message.author.avatar else discord.Embed.Empty,
            )
            
            await author.send(embed=embed, files=files)
            
            for file in files:
                file.reset()
            
            await ctx.channel.send(embed=embed, files=files)
            await ctx.message.delete()
            
            await self.db.ModMail.find_one_and_update({"thread_id": ctx.channel.id, "open": True}, {"$set": {"open": False}})
            await ctx.channel.edit(name=f"{author.name}#{author.discriminator} | {author.id}", archived=True, locked=True)
            
            e = Embed(title="Closed Ticket", colour=0xFF0000, timestamp=True)
            e.set_footer(
                f"{author.name}#{author.discriminator} | {author.id}",
                author.avatar.url if author.avatar else discord.Embed.Empty,
            )
            
            msg = ctx.channel.parent.get_partial_message(data.get("message_id", 0))
            
            await msg.edit(embed=e)
            
            
        
        
setup = lambda bot: bot.add_cog(ThreadListener(bot))
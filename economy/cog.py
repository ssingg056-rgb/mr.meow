import discord
from discord.ext import commands

ALLOWED_GUILD_IDS = [
    1413541161024360511,
    1533591364724326551,
    1525429155049639977,
    1520755884693913703,
]

EMBED_COLOR = discord.Color.gold()


class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        print(f"DEBUG: Received message -> {message.content}")
        if message.author.bot:
            return
        if ALLOWED_GUILD_IDS and (message.guild is None or message.guild.id not in ALLOWED_GUILD_IDS):
            return
        if message.content.startswith(("mr.", "Mr.")):
            return
        if hasattr(self.bot, "economy") and self.bot.economy:
            await self.bot.economy.message_reward(message.guild.id, message.author.id)

    @commands.command(name="balance")
    async def balance(self, ctx):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        bal = await self.bot.economy.get_balance(ctx.guild.id, ctx.author.id)
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        await ctx.send(f"**{ctx.author.display_name}**'s balance: `{bal}` {symbol}")

    @commands.command(name="daily")
    async def daily(self, ctx):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        success, msg, new_bal = await self.bot.economy.claim_daily(ctx.guild.id, ctx.author.id)
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        emoji = "✅" if success else "⏰"
        reply = f"{emoji} {msg}"
        if success:
            reply += f" | New balance: `{new_bal}` {symbol}"
        await ctx.send(reply)

    @commands.command(name="weekly")
    async def weekly(self, ctx):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        success, msg, new_bal = await self.bot.economy.claim_weekly(ctx.guild.id, ctx.author.id)
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        emoji = "✅" if success else "⏰"
        reply = f"{emoji} {msg}"
        if success:
            reply += f" | New balance: `{new_bal}` {symbol}"
        await ctx.send(reply)

    @commands.command(name="send")
    async def send(self, ctx, member: discord.Member, amount: int):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return
        success, msg = await self.bot.economy.transfer(ctx.guild.id, ctx.author.id, member.id, amount)
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        emoji = "💸" if success else "❌"
        await ctx.send(f"{emoji} {msg} {symbol}")

    @commands.command(name="gamble")
    async def gamble(self, ctx, amount: int):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return
        success, msg, new_bal = await self.bot.economy.gamble(ctx.guild.id, ctx.author.id, amount)
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        emoji = "🎉" if success else "💸"
        await ctx.send(f"{emoji} {msg} | Balance: `{new_bal}` {symbol}")

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx, page: int = 1):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        entries = await self.bot.economy.get_leaderboard(ctx.guild.id, max(page, 1))
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        if not entries:
            await ctx.send("No one has coins yet!")
            return
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, entry in enumerate(entries):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            user_id = entry["user_id"]
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"Unknown({user_id})"
            lines.append(f"{medal} **{name}** — `{entry['balance']}` {symbol}")
        embed = discord.Embed(
            title=f"🏆 Leaderboard — Page {page}",
            description="\n".join(lines),
            color=EMBED_COLOR,
        )
        await ctx.send(embed=embed)

    @commands.command(name="shop")
    async def shop(self, ctx):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        items = await self.bot.economy.get_shop(ctx.guild.id)
        symbol = (await self.bot.economy.config.get_currency_info(ctx.guild.id))["symbol"]
        if not items:
            await ctx.send("The shop is empty!")
            return
        lines = []
        for item in items:
            stock = f" *(stock: {item[3]})*" if len(item) > 3 and item[3] is not None else ""
            lines.append(f"**{item[0]}** – `{item[1]}`{symbol}{stock}\n{item[2]}")
        embed = discord.Embed(
            title="🛒 Shop",
            description="\n\n".join(lines),
            color=EMBED_COLOR,
        )
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, item_name: str, quantity: int = 1):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        if quantity < 1:
            await ctx.send("Quantity must be at least 1!")
            return
        success, msg = await self.bot.economy.buy_item(
            ctx.guild.id,
            ctx.author.id,
            item_name,
            quantity,
            bot_member=ctx.guild.me,
            user_member=ctx.author,
        )
        emoji = "✅" if success else "❌"
        await ctx.send(f"{emoji} {msg}")

    @commands.command(name="addshopitem")
    @commands.has_permissions(manage_guild=True)
    async def addshopitem(self, ctx, name: str, price: int, description: str):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        success, msg = await self.bot.economy.add_shop_item(ctx.guild.id, name, price, description)
        await ctx.send(f"{'✅' if success else '❌'} {msg}")

    @commands.command(name="removeshopitem")
    @commands.has_permissions(manage_guild=True)
    async def removeshopitem(self, ctx, name: str):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        success, msg = await self.bot.economy.remove_shop_item(ctx.guild.id, name)
        await ctx.send(f"{'✅' if success else '❌'} {msg}")

    @commands.command(name="give")
    @commands.has_permissions(administrator=True)
    async def give(self, ctx, member: discord.Member, amount: int):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        success, msg, _ = await self.bot.economy.admin_give(ctx.guild.id, member.id, amount)
        await ctx.send(f"{'✅' if success else '❌'} {msg}")

    @commands.command(name="take")
    @commands.has_permissions(administrator=True)
    async def take(self, ctx, member: discord.Member, amount: int):
        if ALLOWED_GUILD_IDS and ctx.guild.id not in ALLOWED_GUILD_IDS:
            return
        success, msg, _ = await self.bot.economy.admin_take(ctx.guild.id, member.id, amount)
        await ctx.send(f"{'✅' if success else '❌'} {msg}")

    @commands.command(name="hunt")
    async def hunt(self, ctx):
        # Check if the user has an Iron Sword in their inventory
        has_sword = await self.bot.economy.has_item(ctx.guild.id, ctx.author.id, "Iron Sword")
        
        if not has_sword:
            await ctx.send("❌ You need an **Iron Sword** from the `?shop` before you can go hunting!")
            return
            
        reward = 75
        await self.bot.economy.add_money(ctx.guild.id, ctx.author.id, reward)
        await ctx.send(f"🗡️ You went hunting with your Iron Sword and brought back game worth {reward} gold!")

    @commands.command(name="fish")
    async def fish(self, ctx):
        # Check if the user has a Fishing Rod
        has_rod = await self.bot.economy.has_item(ctx.guild.id, ctx.author.id, "Fishing Rod")
        
        if not has_rod:
            await ctx.send("❌ You need a **Fishing Rod** from the `?shop` to catch fish!")
            return
            
        reward = 50
        await self.bot.economy.add_money(ctx.guild.id, ctx.author.id, reward)
        await ctx.send(f"🎣 You cast your line and caught a big fish, selling it for {reward} gold!")

    @commands.command(name="mine")
    async def mine(self, ctx):
        # Check if the user has a Pickaxe
        has_pickaxe = await self.bot.economy.has_item(ctx.guild.id, ctx.author.id, "Iron Pickaxe")
        
        if not has_pickaxe:
            await ctx.send("❌ You need an **Iron Pickaxe** from the `?shop` to go mining!")
            return
            
        reward = 100
        await self.bot.economy.add_money(ctx.guild.id, ctx.author.id, reward)
        await ctx.send(f"⛏️ You mined deep into the caves and struck ore worth {reward} gold!")

    @commands.command(name="addshopitem")
    @commands.has_permissions(administrator=True)
    async def addshopitem(self, ctx, price: int, name: str, *, description: str):
        # Inserts the item into your economy system's shop database for this specific server
        await self.bot.economy.add_item(ctx.guild.id, name=name, price=price, description=description)
        await ctx.send(f"✅ Successfully added **{name}** to the shop for {price} gold!")


async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
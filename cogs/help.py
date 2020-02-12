import discord
from discord.ext import commands

class AwotHelp(commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'cooldown': commands.Cooldown(1, 3.0, commands.BucketType.member),
            'help': 'Shows help about the bot, a command, or a category.'
        })

    async def send_bot_help(self, mapping):

        ctx = self.context

        description = f"Use `{ctx.prefix}help [Command/Category]` for more info on a command or category.\n"

        for cog in sorted(ctx.bot.cogs.values(), key=lambda cog: cog.qualified_name):

            if ctx.author.id in ctx.bot.owner_ids:
                cog_commands = [command for command in cog.get_commands()]
            else:
                cog_commands = [
                    command for command in cog.get_commands() if command.hidden == False]

            if len(cog_commands) == 0:
                continue

            cog_commands.sort(key=lambda c: c.name)

            description += f"\n__**{cog.qualified_name}:**__\n"

            for command in cog_commands:
                command_help = embedify(command.help)
                description += f"`{command.name}` \u200b \u200b {command_help}\n"

        embed = discord.Embed(
            colour=discord.Color.blue(),
            title=f"__{ctx.bot.user.name}'s help page__",
            description=description
        )

        await ctx.send(embed=embed)

class Help(commands.Cog):
    """
    Help Cog
    """

    def __init__(self, bot):
        self.bot = bot
        self.old_help_command = self.bot.help_command
        self.bot.help_command = AwotHelp()
        self.bot.help_command.cog = self

def embedify(text: str, len: int = 55) -> str:
    text = text[:len] + (text[len:] and '..')
    return text

def setup(bot):
    bot.add_cog(Help(bot))
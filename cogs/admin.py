import discord
from discord.ext import commands

import asyncio
import traceback
import textwrap
from contextlib import redirect_stdout
import io
import subprocess

class Admin(commands.Cog):
    """Admin-only commands that make the bot dynamic."""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def reload_or_load_extension(self, module):
        try:
            self.bot.reload_extension(f"cogs.{module.lower()}")
        except commands.ExtensionNotLoaded:
            self.bot.load_extension(f"cogs.{module.lower()}")

    @commands.command(hidden=True)
    async def load(self, ctx, *, module):
        """Loads a module."""
        try:
            self.reload_or_load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(hidden=True)
    async def unload(self, ctx, *, module):
        """Unloads a module."""
        try:
            self.bot.unload_extension(f"cogs.{module.lower()}")
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.group(name='reload', hidden=True, invoke_without_command=True, aliases=["r"])
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        try:
            self.reload_or_load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @_reload.command(name='all', hidden=True)
    async def _reload_all(self, ctx):
        """
        Reloads all modules, while pulling from git.
        """

        if ctx.author.id not in self.bot.owner_ids:
            await ctx.send("You do not have permission for this command.")
            return

        msg = await ctx.send("Reloading all cogs..\n")
        content = msg.content + "\n"

        cogs = list(self.bot.cogs)
        successful_reloads = 0
        temp = ""
        for cog in cogs:
            cog = cog.lower()
            try:
                self.reload_or_load_extension(cog)
                temp = f"✅ Reloaded cog: `{cog}`\n"
                successful_reloads += 1
            except Exception as e:
                temp = f'❌ {e.__class__.__name__}: {e}\n'
            content += temp

        content += f"\nSuccessfully reloaded [ {successful_reloads} / {len(cogs)} ]"
        await msg.edit(content=content)
        if successful_reloads == len(cogs):
            await msg.add_reaction("👍")
        else:
            await msg.add_reaction("👎")

    @commands.command(name='gitpull', hidden=True)
    async def _git_pull(self, ctx):
        """Reloads all modules, while pulling from git."""

        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')

        if stdout.startswith('Already up to date.'):
            return await ctx.send(stdout)

        cmd = self.bot.get_command("reload all")
        await cmd(ctx)

    @commands.command(pass_context=True, hidden=True, name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(name='stop')
    async def _stop(self, ctx):
        """Stops the bot"""

        await self.bot.close()

def setup(bot):
    bot.add_cog(Admin(bot))

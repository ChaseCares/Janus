from discord.ext import commands
from collections import defaultdict
from dotenv import load_dotenv
import discord
import os


# files
from janus_log import setupLogger
import janus_updater as ju


load_dotenv('./config/.env')
TOKEN = os.getenv('DISCORD_TOKEN')
JANUS_CHANNEL = int(os.getenv('JANUS_CHANNEL'))

COMMAND_PREFIX = '!'

# emoji
EMOJI_CONFIRM = "\N{WHITE HEAVY CHECK MARK}"


# Dialogue
DIA_TRY_AGAIN_LATER = "Robot is working, try again later"
DIA_UPDATE_SUCCESS = "Robot should be rebooting"
DIA_UPDATE_IN_PROGRESS ="Update in progress."
DIA_ERROR_WITH_BUILT = "Error while build"
DIA_TRANSFERRING = 'Transferring binary to:'
DIA_CONFIRM_UPDATE = "Confirm update?"
DIA_BUILD_SUCCESS = "Build successful"
DIA_BOT_IS_READY = "Bot is ready"
DIA_BUILD_FAILED = "Build failed"
DIA_ABORTING  = "Aborting"
DIA_UPDATING  = "Updating"
DIA_BUILDING = "Building"


processQueue = defaultdict(list)
updateQueue = list()


bot = commands.Bot(command_prefix=COMMAND_PREFIX)
log = setupLogger(ju.LOG_NAME, ju.PATH_LOG)


async def add_reaction(message, reactions):
    for emoji in reactions:
        await message.add_reaction(emoji)


async def remove_reaction(message, all=True):
    for reaction in message.reactions:
        for user in await reaction.users().flatten():
            if all:
                await reaction.remove(user)
            elif user != bot.user:
                await reaction.remove(user)


@bot.command(name='build', aliases=['b'])
async def build(ctx):
    await ctx.send(DIA_BUILDING)
    if ju.build():
        await ctx.send(DIA_BUILD_SUCCESS)
    else:
        await ctx.send(DIA_BUILD_FAILED)


async def update(ctx):
    if len(updateQueue) >= 1:
        if not ju.buildCheck():
            await build(ctx)
        if ju.buildCheck():
            for robot in updateQueue:
                if ju.docked(ju.loadConfig(f"{robot}.ini")):
                    await ctx.send(f"{DIA_TRANSFERRING} {robot}")
                    ju.sshHandler(ju.loadConfig(f'{robot}.ini'))
                    updateQueue.remove(robot)
                    await ctx.send(DIA_UPDATE_SUCCESS)
                else:
                    updateQueue.remove(robot)
                    await ctx.send(DIA_TRY_AGAIN_LATER)
        else:
            await ctx.send(DIA_ERROR_WITH_BUILT)


@bot.command(name='checkUpdate', aliases=['cu'])  # updateCheck?
async def checkUpdate(ctx):
    for configFile in os.listdir(ju.PATH_ROBOTS):
        config = ju.loadConfig(configFile)
        if ju.checkUpdate(config['ROBOT']['ip']):
            message = await ctx.send(f"Robot {config['ROBOT']['name']} requires update", delete_after=30.0)
            processQueue[message.id] = [EMOJI_CONFIRM, config['ROBOT']['name']]
            await add_reaction(message, EMOJI_CONFIRM)
        else:
            await ctx.send(f"Robot {config['ROBOT']['name']} is up-to-date")


@bot.event
async def on_reaction_add(reaction, user):
    channel = bot.get_channel(JANUS_CHANNEL)
    if not user.bot:
        if processQueue[reaction.message.id][0] == EMOJI_CONFIRM:
            await channel.send(f"{DIA_UPDATING} {processQueue[reaction.message.id][1]}.")
            updateQueue.append(processQueue[reaction.message.id][1])
            await remove_reaction(reaction.message)
            await update(await bot.get_context(reaction.message))


@bot.event
async def on_ready():
    channel = bot.get_channel(JANUS_CHANNEL)
    await channel.send(DIA_BOT_IS_READY)


bot.run(TOKEN)

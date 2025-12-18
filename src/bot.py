import os
import random
import re
import smtplib
import sqlite3

import discord

from odoo import Odoo

intents = discord.Intents.default()
intents.members = True
intents.messages = True

bot = discord.Bot(intents=intents)


def db_setup():
    db = sqlite3.connect("/data/discord.db")
    cur = db.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS users
                (
                  id INT NOT NULL PRIMARY KEY,
                  email VARCHAR(25),
                  code VARCHAR(6),
                  verified INT DEFAULT 0

                );"""
    )
    db.commit()
    return db


db = db_setup()
odoo = Odoo()


def send_email_code(db, email, user_id):
    cur = db.cursor()
    code = str(random.randint(0, 999999)).zfill(6)
    print(f"Code {code}")
    cur.execute("SELECT * FROM users WHERE id  = ?", (user_id,))
    if len(cur.fetchall()) == 0:
        cur.execute(
            "INSERT INTO users (id, email, code) VALUES (?, ?, ?)",
            (
                user_id,
                email,
                code,
            ),
        )
    else:
        cur.execute(
            "UPDATE users SET email = ?, code = ? where id = ?",
            (
                email,
                code,
                user_id,
            ),
        )
    db.commit()
    with smtplib.SMTP_SSL("smtp-relay.gmail.com", 465) as smtp:
        subject = "ICT Scouts Discord Verifizierung"
        headers = "From: ICT Scouts Discord <discord@ict-scouts.ch>\n"
        headers += f"To: {email}"
        body = (
            f"Hallo,\n\nDein Bestätigungscode lautet: {code}\n\nViel Spass,\nICT Scouts"
        )
        msg = f"Subject: {subject}\n{headers}\n\n{body}"
        try:
            smtp.sendmail(
                os.getenv("EMAIL_USER", "discord@ict-scouts.ch"),
                email,
                msg.encode("utf-8"),
            )
        except Exception as e:
            print(e)
            return False

    return True


async def validate_user(ctx, db, user_id, code):
    cur = db.cursor()
    cur.execute("SELECT email, code FROM users WHERE id = ?", (user_id,))
    data = cur.fetchone()
    stored_code = data[1]
    if stored_code == code:
        # Update the DB
        cur.execute("UPDATE users SET verified = 1 WHERE id = ?", (user_id,))
        db.commit()
        # Add the Member Role to the user
        guild_id = os.getenv("GUILD_ID", None)
        if guild_id is None:
            return "Es ist ein Fehler aufgetreten. `(NO_GUILD_ID)`"
        if not (guild := bot.get_guild(int(guild_id))):
            return "Es ist ein Fehler aufgetreten. `(GUILD_NOT_FOUND)`"

        if not (guild_member := guild.get_member(user_id)):
            return "Es ist ein Fehler aufgetreten. `(MEMBER_NOT_ON_DISCORD)`"

        if not (
            role_id := next(iter([r.id for r in guild.roles if r.name == "Member"]))
        ):
            return "Es ist ein Fehler aufgetreten. `(ROLE_NOT_FOUND)`"

        if not (role := guild.get_role(role_id)):
            return "Es ist ein Fehler aufgetreten. `(ROLE_NOT_FOUND)`"

        await guild_member.add_roles(role)
        await sync_user_role(ctx, user_id, data[0])
        return "Du wurdest erfolgreich verifiziert und hast jetzt Zugang zum Discord."
    else:
        return "Der eingegebene Code ist falsch."


async def get_guild(ctx):
    """Get a guild object from the bot."""
    guild_id = os.getenv("GUILD_ID", None)
    if guild_id is None:
        await ctx.respond("Es ist ein Fehler aufgetreten. `(NO_GUILD_ID)`")
        return False
    if not (guild := bot.get_guild(int(guild_id))):
        await ctx.respond("Es ist ein Fehler aufgetreten. `(GUILD_NOT_FOUND)`")
        return False
    return guild


async def get_server_member(ctx, user_id):
    """Get a member object from the bot."""
    if not (guild := await get_guild(ctx)):
        return False
    if not (guild_member := guild.get_member(user_id)):
        await ctx.respond("Es ist ein Fehler aufgetreten. `(MEMBER_NOT_ON_DISCORD)`")
        return False
    return guild_member


async def ensure_moderator(ctx, user_id):
    """Check if a user is a moderator."""
    if not (user_obj := await get_server_member(ctx, user_id)):
        return False
    if not isinstance(user_obj, discord.Member):
        return False
    roles = user_obj.roles
    # Ensure "Moderator" role is present
    if not (next(iter([r for r in roles if r.name == "Moderator"]), None)):
        await ctx.respond("Du hast keine Berechtigung, diesen Befehl zu benutzen.")
        return False
    return True


async def get_and_create_role(ctx, role_name):
    # Get the Guild object
    if not (guild := await get_guild(ctx)):
        return False
    # Get the Guild roles
    guild_roles = guild.roles
    # Find the role, if not found, create it
    role = next(iter([r for r in guild_roles if r.name == role_name]), None)
    if not role:
        role = await guild.create_role(name=role_name)
    return role


async def sync_user_role(ctx, user_id, user_mail):
    # Get discord member and odoo role
    if not (discord_member := await get_server_member(ctx, user_id)):
        return False
    if not isinstance(discord_member, discord.Member):
        return False
    odoo_role = odoo.get_campus_name(user_mail)
    # Skip empty roles
    if odoo_role == "" or not odoo_role:
        return False
    # Get role object / create if not exists
    discord_role = await get_and_create_role(ctx, odoo_role)
    if not discord_role:
        return False
    # Assign role to member
    await discord_member.add_roles(discord_role)
    return True


@bot.event
async def on_member_join(member):
    await member.send(
        "Willkommen auf dem ICT Scouts Discord. Bitte gib deine `@ict-scouts.ch`-Mail an, um deinen Account zu bestätigen."
    )


@bot.event
async def on_message(message):
    # Only react to messages in a private channel
    if type(message.author) == discord.Member:
        return
    user_id = message.author.id
    # Ignore self-messages from the bot
    if bot.user.id == user_id:  # pyright: ignore
        return
    msg = message.content
    # If message content is a valid campus e-mail
    if re.match(r"\w+\.\w+@ict-scouts\.ch", msg):
        if send_email_code(db, msg, user_id):
            await message.author.send(
                "Wir haben dir eine E-Mail zur Bestätigung gesendet. Bitte gib den enthaltenen Code zur Bestätigung ein."
            )
        else:
            await message.author.send(
                "Beim Versenden der E-Mail ist ein Fehler aufgetreten."
            )
    # If message content is a code
    elif re.match("[0-9]{6}", msg):
        await message.author.send(await validate_user(message, db, user_id, msg))
    # Any other messages
    else:
        await message.author.send(
            "Keine gültige E-Mail oder Bestätigungscode angegeben"
        )


@bot.command(description="Show email of a user")
async def userinfo(ctx, u: discord.User):
    # Ensure user is in group
    author_id = ctx.author.id
    if not await ensure_moderator(ctx, author_id):
        return
    # Get the user info
    user_id = u.id
    cur = db.cursor()
    cur.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    data = cur.fetchone()
    if len(data) == 0:
        await ctx.respond("Benutzer ist noch nicht verifiziert.")
    await ctx.respond(f"Userinfo für <@{user_id}>: `{data[0]}`")


@bot.command(description="Print user list")
async def print_userlist(ctx):
    # Ensure user is moderator
    author_id = ctx.author.id
    if not await ensure_moderator(ctx, author_id):
        return
    # Get all verified users from DB
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE verified = 1")
    data = cur.fetchall()
    output = "Aktuelle Benutzer:\n"
    for user in data:
        if len(output) > 1800:
            await ctx.respond(output)
            output = ""
        output += f"<@{user[0]}>: `{user[1]}`\n"
    return await ctx.respond(output)


@bot.command(description="Sync all member roles")
async def sync_roles(ctx):
    # Ensure user is moderator
    author_id = ctx.author.id
    if not await ensure_moderator(ctx, author_id):
        return
    # Get all verified users from DB
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE verified = 1")
    data = cur.fetchall()
    results = []
    for user in data:
        # Sync user roles
        results.append(await sync_user_role(ctx, user[0], user[1]))
    success = results.count(True)
    failed = results.count(False)
    await ctx.respond(
        f"Rollen wurden erfolgreich synchronisiert. ({success} erfolgreich, {failed} fehlgeschlagen)"
    )


bot.run(os.getenv("BOT_TOKEN"))

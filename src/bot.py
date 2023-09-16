import os
import random
import re
import smtplib
import sqlite3

import discord

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


async def validate_user(db, user_id, code):
    cur = db.cursor()
    cur.execute("SELECT code FROM users WHERE id = ?", (user_id,))
    stored_code = cur.fetchone()[0]
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

        return "Du wurdest erfolgreich verifiziert und hast jetzt Zugang zum Discord."
    else:
        return "Der eingegebene Code ist falsch."


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
        await message.author.send(await validate_user(db, user_id, msg))
    # Any other messages
    else:
        await message.author.send(
            "Keine gültige E-Mail oder Bestätigungscode angegeben"
        )


@bot.command(description="Show email of a user")
async def userinfo(ctx, u: discord.User):
    # Ensure user is in group
    author_id = ctx.author.id
    guild_id = os.getenv("GUILD_ID", None)
    if guild_id is None:
        return await ctx.respond("Es ist ein Fehler aufgetreten. `(NO_GUILD_ID)`")
    if not (guild := bot.get_guild(int(guild_id))):
        return await ctx.respond("Es ist ein Fehler aufgetreten. `(GUILD_NOT_FOUND)`")
    if not (guild_member := guild.get_member(author_id)):
        return await ctx.respond(
            "Es ist ein Fehler aufgetreten. `(MEMBER_NOT_ON_DISCORD)`"
        )
    roles = guild_member.roles
    # Ensure "Moderator" role is present
    if not (next(iter([r for r in roles if r.name == "Moderator"]), None)):
        return await ctx.respond(
            "Du hast keine Berechtigung, diesen Befehl zu benutzen."
        )

    user_id = u.id
    cur = db.cursor()
    cur.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    email = cur.fetchone()[0]
    await ctx.respond(f"**Userinfo for <@{user_id}>:** `{email}`")


bot.run(os.getenv("BOT_TOKEN"))

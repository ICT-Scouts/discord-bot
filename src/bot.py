import os
import random
import re
import sqlite3

import discord

intents = discord.Intents.default()
intents.members = True
intents.messages = True

bot = discord.Bot(intents=intents)


def db_setup():
    db = sqlite3.connect("discord.db")
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
    return True


def validate_user(db, user_id, code):
    cur = db.cursor()
    cur.execute("SELECT code FROM users WHERE id = ?", (user_id,))
    stored_code = cur.fetchone()[0]
    if stored_code == code:
        cur.execute("UPDATE users SET verified = 1 WHERE id = ?", (user_id,))
        db.commit()
        return (
            "Du wurdest erfolgreich verifiziert und kannst den Server jetzt benutzen."
        )
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
    if re.match(r"\w+\.\w+@ict-scouts\.ch", msg):
        if send_email_code(db, msg, user_id):
            await message.author.send(
                "Wir haben dir eine E-Mail zur Bestätigung gesendet. Bitte gib den enthaltenen Code zur Bestätigung ein."
            )
        else:
            await message.author.send(
                "Beim Versenden der E-Mail ist ein Fehler aufgetreten."
            )
    elif re.match("[0-9]{6}", msg):
        await message.author.send(validate_user(db, user_id, msg))
    else:
        await message.author.send(
            "Keine gültige E-Mail oder Bestätigungscode angegeben"
        )


bot.run(os.getenv("BOT_TOKEN"))

import argparse
import asyncio
import csv
import os
import re
import sys

import aiohttp
import discord


def safe_filename(name: str) -> str:
    return re.sub(r'[^\w\-. ]', '_', name)[:100]


async def download_avatar(session: aiohttp.ClientSession, member: discord.Member, out_dir: str):
    url = member.display_avatar.replace(size=512).url
    filename = f"{safe_filename(str(member))}_{member.id}.png"
    path = os.path.join(out_dir, filename)
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(path, "wb") as f:
                    f.write(await resp.read())
                return True
    except Exception as e:
        print(f"  ! failed to download avatar for {member}: {e}")
    return False


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guild-id", type=int, default=None)
    parser.add_argument("--output", default="members.csv")
    parser.add_argument("--download-avatars", action="store_true", default=True)
    parser.add_argument("--avatar-dir", default="avatars")
    parser.add_argument("--include-bots", action="store_true")
    args = parser.parse_args()

    token_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token and os.path.exists(token_cache_path):
        with open(token_cache_path, "r", encoding="utf-8") as f:
            token = f.read().strip()
        if token:
            print("Using saved token from token.txt")
    if not token:
        token = input("Paste your Discord bot token here and press Enter: ").strip()
        if token:
            save = input("Save this token locally so you don't have to paste it again? (y/n): ").strip().lower()
            if save == "y":
                with open(token_cache_path, "w", encoding="utf-8") as f:
                    f.write(token)
                print(f"Saved to {token_cache_path}")
    if not token:
        print("ERROR: no token provided.")
        sys.exit(1)

    if args.guild_id is None:
        guild_input = input("Paste the Server (Guild) ID to export from: ").strip()
        try:
            args.guild_id = int(guild_input)
        except ValueError:
            print("ERROR: invalid server ID.")
            sys.exit(1)

    intents = discord.Intents.default()
    intents.members = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Logged in as {client.user}")
        guild = client.get_guild(args.guild_id)
        if guild is None:
            print("ERROR: bot is not in that guild, or guild ID is wrong.")
            await client.close()
            return

        print(f"Fetching members from '{guild.name}'...")
        members = []
        async for member in guild.fetch_members(limit=None):
            if not args.include_bots and member.bot:
                continue
            members.append(member)
        print(f"Fetched {len(members)} members.")

        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "username", "display_name", "avatar_url"])
            for m in members:
                writer.writerow([
                    m.id,
                    str(m),
                    m.display_name,
                    m.display_avatar.replace(size=512).url,
                ])
        print(f"Wrote {args.output}")

        if args.download_avatars:
            os.makedirs(args.avatar_dir, exist_ok=True)
            print(f"Downloading avatars to ./{args.avatar_dir}/ ...")
            connector = aiohttp.TCPConnector(limit=10)
            async with aiohttp.ClientSession(connector=connector) as session:
                sem = asyncio.Semaphore(10)

                async def worker(m):
                    async with sem:
                        await download_avatar(session, m, args.avatar_dir)

                await asyncio.gather(*(worker(m) for m in members))
            print("Done downloading avatars.")

        await client.close()

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())

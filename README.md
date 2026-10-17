# Waru-AI

Telegram AI assistant for Waru Edition and Command & Conquer: Generals / Zero Hour.

## Features

- OpenAI-powered responses in Uzbek, Russian, and English.
- Per-user short conversation context and `/reset`.
- `/latest` shows configured release information and will not invent URLs.
- `/files` lists configured downloads and Telegram channel posts.
- `/tutorials` lists tutorial video links.
- `/analyze` (admin only) explains how to analyze older posts by forwarding their media to the bot.
- New channel media posts are indexed with metadata-based AI notes; APK/ZIP inspection is limited by Telegram download size.
- Admin commands to update release metadata and community links.
- GitHub Actions checks Python syntax and the JSON catalog.

## 1. Create a Telegram bot

Open [@BotFather](https://t.me/BotFather), send `/newbot`, and copy the token.

## 2. Configure environment

Python 3.11+ is recommended.

Windows:

```bat
py -m venv .venv
.venv\\Scripts\\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and enter your Telegram bot token and OpenAI API key. Set `ADMIN_IDS` to your numeric Telegram user ID. **Never commit `.env` or publish API keys.** ChatGPT subscription and API billing are separate.

Run:

```bash
python bot.py
```

Keep the process running to keep the bot online. For 24/7 operation, deploy to a trusted server and configure the same environment variables there.

## 3. Add real releases, files and tutorial videos

Edit `catalog.json` with the real links you control. Supported destinations include direct downloads, public Telegram posts (`https://t.me/channel/123`), YouTube tutorials, and other HTTPS pages. A `url` is the direct destination. `telegram_post_url` opens a channel post.

Example:

```json
{
  "version": {
    "name": "Waru Edition",
    "latest_version": "1.2.3",
    "release_notes": "Bug fixes and improvements",
    "download_url": "https://example.com/WaruEdition.apk",
    "telegram_post_url": "https://t.me/your_channel/123",
    "updated_at": "2026-10-17"
  },
  "files": [
    {
      "name": "Waru Edition APK",
      "description": "Android release",
      "url": "https://example.com/WaruEdition.apk",
      "telegram_post_url": "https://t.me/your_channel/123"
    }
  ],
  "tutorials": [
    {
      "title": "How to install Waru Edition",
      "description": "Installation walkthrough",
      "url": "https://youtu.be/your_video_id"
    }
  ],
  "support_channel": "https://t.me/your_channel",
  "support_group": "https://t.me/your_group"
}
```

Replace every example URL with a real, authorized link. Placeholder URLs do not work. Private Telegram channel posts may require the bot to be a member or a valid invite link. The bot indexes new supported channel media posts and attempts a metadata-based AI analysis. Telegram Bot API cannot fetch arbitrary historical channel posts on demand, so admins should forward old media posts to the bot for analysis. Video content itself is not fully transcribed or visually analyzed by this implementation.

## 4. Admin commands

Once `ADMIN_IDS` is set:

- `/adminhelp` — list admin commands
- `/setversion 1.2.3 | https://example.com/file.apk | Release notes`
- `/setchannel https://t.me/your_channel`
- `/setgroup https://t.me/your_group`

The `/setversion` command writes to `catalog.json` on the running host. On ephemeral deployment platforms, file changes may disappear at redeploy; keep configuration in persistent storage or your deployment configuration. The bot process needs write access to the catalog.

## Commands

- `/start`
- `/help`
- `/latest`
- `/files`
- `/tutorials`
- `/reset`


## 5. Send actual files and videos from your Telegram channel

This bot can copy a channel post (including its attached APK/file/video) into the user's chat. The bot must be added to the source channel; use a channel username such as `@your_channel` or the numeric channel ID such as `-1001234567890`.

In `catalog.json`, configure the latest release source:
```json
"source_chat_id": "@your_channel",
"source_message_id": 123
```

Add `source_chat_id` and `source_message_id` to each object in `files` and `tutorials` in the same way. Use the message ID of the original channel post that contains the file or video. You can keep `url` and `telegram_post_url` too as fallback links.

Example file entry:
```json
{
  "name": "Waru Edition APK",
  "description": "Latest Android release",
  "url": "https://example.com/WaruEdition.apk",
  "telegram_post_url": "https://t.me/your_channel/123",
  "source_chat_id": "@your_channel",
  "source_message_id": 123
}
```

The bot will use Telegram's copy-message feature to send the original channel post contents to the requester. It does not remove or delete the channel post. If copying fails, check the channel ID, message ID, and that the bot has access to the source channel. For large files, Telegram Bot API file limits may apply.

## Security and limitations

- Do not upload `.env`, Telegram tokens, OpenAI keys, or logs containing secrets.
- Limit `ADMIN_IDS` to trusted people.
- AI answers use API credits and may incur costs.
- Latest releases are read from the catalog; no release is automatically discovered unless a trusted release feed is added.
- Files and videos appear only after adding valid URLs to `catalog.json`.
- Do not distribute files unless you have permission to publish them.

## License

No license has been selected yet. Add one after deciding how this project may be reused.

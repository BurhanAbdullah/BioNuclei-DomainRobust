# Saving and backing up BioNuclei data locally

## Run BioNuclei on your computer

```
python scripts/run_local.py --checkpoint path/to/bionuclei.pt
```

This starts the analysis server and the website on your computer and opens the Lab. Both listen on 127.0.0.1 only, so nobody else on the network or the internet can reach them.

- Results, reports and job files are saved in `data/` inside the repository (change with `--data D:\BioNuclei\data`).
- Results are kept for 30 days (change with `--keep-days`). You can delete any analysis earlier from the Lab.
- `data/` is excluded from git, so results are never committed by accident.
- Guest mode needs nothing external. Account sign-in still uses Supabase.

## Back up

```
python scripts/run_local.py --backup D:\BioNuclei-backups
```

This writes one `.tar.gz` file with everything in `data/`, then checks that every file in it decrypts. Copy that folder to an external drive if you want a second copy.

To run it daily on Windows, add a Task Scheduler task with the same command. On macOS or Linux, use cron:
`30 2 * * * cd /path/to/BioNuclei-DomainRobust && python3 scripts/run_local.py --backup ~/BioNuclei-backups`

## The key

Stored files are encrypted with AES-256-GCM. The key is created on first run at `~/.bionuclei/data.key` (Windows: `C:\Users\<you>\.bionuclei\data.key`), outside the data folder and readable only by your user account.

**Copy this key somewhere safe, such as a password manager or a USB stick.** Without it, neither the data folder nor a backup can be opened. Keep it away from the backup folder.

## What protects what

| Mechanism | Protects |
|---|---|
| Supabase Auth | Account passwords. BioNuclei never receives or stores them. |
| 127.0.0.1-only servers | Your computer: nothing is exposed to the network. |
| AES-256-GCM, `src/bionuclei/storage.py` | Stored files. A file copied into another user's folder will not decrypt. |
| Per-user folders | `users/<account id>/` and `guests/<digest>/`, never e-mail addresses. |

## Public server (optional)

The hosted Lab on Render works the same way with `BIONUCLEI_DATA_ROOT`, `BIONUCLEI_DATA_KEY` and `BIONUCLEI_BACKUP_TOKEN_SHA256` set (generate them with `scripts/make_storage_secrets.py`). `scripts/pull_backup.py` then copies its backups onto your computer over HTTPS. Your computer only makes outgoing requests.

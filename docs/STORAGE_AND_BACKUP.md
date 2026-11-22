# Storage, encryption and PC backups

The cloud server is the primary store. The administrator's computer keeps backup copies by pulling them on a schedule. The PC never accepts incoming connections.

## What protects what

| Mechanism | Protects | Where |
|---|---|---|
| Supabase Auth | Account passwords (hashed by Supabase; BioNuclei never receives them) | Supabase |
| HTTPS | Data in transit | Render and GitHub Pages |
| AES-256-GCM (`cryptography`) | Stored files at rest | `src/bionuclei/storage.py` |
| Backup token (hash only on server) | The backup download endpoint | `webapp/auth.py` |

Each stored file is encrypted with a fresh nonce. Its path relative to the data root is the GCM associated data, so a file copied into another user's folder will not decrypt. Folder names are account UUIDs or SHA-256 guest digests, never e-mail addresses.

## Layout

```
<BIONUCLEI_DATA_ROOT>/
  users/<account id>/{projects,images,analyses,annotations,reports,exports}/
  guests/<guest digest>/...
  system/backups/        server-side archives (last 3 kept, excluded from backups)
```

## One-time setup

1. On your computer, inside the repository: `python scripts/make_storage_secrets.py`
2. In Render, service `bionuclei-community`, add:
   - `BIONUCLEI_DATA_ROOT=/data/bionuclei-store` (the service's persistent disk is mounted at `/data`)
   - `BIONUCLEI_DATA_KEY=...`
   - `BIONUCLEI_BACKUP_TOKEN_SHA256=...`
3. Save `BIONUCLEI_DATA_KEY` in a password manager. A backup cannot be restored without it.

## Scheduled backup on your PC

Windows (Task Scheduler, daily): action `python`, arguments
`C:\path\to\BioNuclei-DomainRobust\scripts\pull_backup.py --url https://bionuclei-community-analyzer.onrender.com --dest D:\BioNuclei\backups --keep 14`,
with `BIONUCLEI_BACKUP_TOKEN` set as a user environment variable (`setx BIONUCLEI_BACKUP_TOKEN "..."`).

macOS or Linux (cron, 02:30 daily):
`30 2 * * * BIONUCLEI_BACKUP_TOKEN=... /usr/bin/python3 /path/to/scripts/pull_backup.py --url https://bionuclei-community-analyzer.onrender.com --dest ~/BioNuclei/backups`

Setting `BIONUCLEI_DATA_KEY` for the task as well makes the script prove that every file decrypts. Nothing is written in plaintext.

The script refuses plain-HTTP URLs, verifies the server's SHA-256 and every file hash in the manifest, deletes a backup that fails verification and keeps the newest `--keep` archives.

## Current limits

- Analysis jobs are still transient (results expire after the retention window). Saved projects will use this store when project persistence lands.
- If the PC is off, that night's backup is skipped and the next run catches up. The server copy is unaffected.
- Restoring is a manual step: extract `data/` from an archive into the server's data root with the same key.

## Daily backup into Google Drive (no PC needed)

`.github/workflows/backup_to_drive.yml` runs every day at 02:47 IST and copies the encrypted archive into the Drive folder `1IUcF1OuF0beo1e1sLgDOHKyOOF9n8wAY`. Google stores ciphertext only; the data key never leaves the server and your password manager.

One-time setup:
1. Google Cloud Console: create a project, enable the Google Drive API, create an OAuth client of type **Desktop app**.
2. On your computer: `python scripts/drive_authorize.py --client-id ... --client-secret ...` and approve in the browser with the Google account that owns the folder.
3. GitHub repository > Settings > Secrets and variables > Actions, add secrets `GDRIVE_CLIENT_ID`, `GDRIVE_CLIENT_SECRET`, `GDRIVE_REFRESH_TOKEN`, `BIONUCLEI_BACKUP_TOKEN`, and `BIONUCLEI_DATA_KEY` (the same data key as the server; do not print it or place it in artifacts). For a custom HTTPS server, set the repository variable `BIONUCLEI_BACKUP_ALLOWED_HOST` to that exact hostname.
4. Actions > Backup to Google Drive > Run workflow, to test it once.

Until the secrets exist, the workflow finishes with a "not configured" warning. It keeps the newest 30 backups and only ever deletes files it uploaded itself.

The PC route above still works as a second copy: point `--dest` at a folder inside Google Drive for Desktop to sync it as well.

# bashdrop

**bashdrop** is a tiny one-shot file transfer tool.

It is designed for situations where the **sender and receiver only have Bash** and raw TCP via `/dev/tcp`.

That means: no `scp`, no `rsync`, no `wormhole`, no `croc`, no `curl`, no `wget`, no `netcat`.
Just Bash. (Optionally `openssl` and `sha256sum` for integrity and encryption modes.)

A **temporary Python relay server** is required somewhere on the internet:
- It can be bootstrapped automatically over **SSH** (with `bashdrop`).
- Or started manually.

> [!NOTE]
> The SSH/scp dependency exists **only to set up the server**.
> Neither the sender nor the receiver need them — they just run Bash commands.

## Files

- **bashdrop** — the main script. Copies `bashdrop-server.py` to a remote machine over SSH and runs it there.
- **bashdrop-server.py** — the Python server that handles one upload and one download. Can also be run directly if you're already on the host.

## Installation with Nix

Test it out without installation:

```sh
nix run . -- <ssh-target> <public-domain-or-ip> [filename] [password]
```

Install it permanently:

```sh
nix profile add github:fabian-thomas/bashdrop
```

## Usage

### Step 1: Start a Relay Server

You need a reachable server somewhere (e.g. a VPS).
There are two ways to start the relay:

1. **Bootstrap via SSH (automatic):**
   ```sh
   bashdrop [-p PORT] <ssh-target> <public-domain-or-ip> [filename] [password]
   ```
   This uses `ssh`/`scp` to copy and start `bashdrop-server.py`.

   Example:
   ```sh
   bashdrop user@myserver my-domain-or-ip.com
   ```

2. **Manual start (no SSH needed):**
   If you already have access to the server shell:
   ```sh
   bashdrop-server.py [-p PORT] <public-host-or-ip> [filename] [password]
   ```

> [!IMPORTANT]
> The `<ssh-target>` and `<public-domain-or-ip>` must point to the **same machine**.
> - `<ssh-target>` → how you connect via SSH (e.g. `user@myserver`)
> - `<public-domain-or-ip>` → how sender/receiver connect (e.g. `my-domain-or-ip.com`)

### Step 2: Send/Receive the File

Once the server is running, it prints ready-to-use **Sender** and **Receiver** commands in three modes:

1. **Plain Bash** — just `/dev/tcp`
2. **Plain + Integrity Check** — `/dev/tcp` with `sha256sum` verification
3. **Encrypted + Integrity Check** — `openssl enc -aes-256-cbc -pbkdf2` with `sha256sum`

These commands require only:
- Bash + `/dev/tcp`
- (optional) `sha256sum`
- (optional) `openssl`

No `ssh`, no `scp`.

### Options

- `-p PORT`: TCP port to listen on (default: `9000`).
- `filename`: filename shown in the copy-paste commands (default: `file`).
- `password`: optional, used only for the encrypted mode (default: random).

Port `9000` is used by default.
Ensure port forwarding / firewall rules allow access.

## Minimal Send/Recv Example

Sender:

```sh
cat >/dev/tcp/my-domain-or-ip.com/9000 < myfile.txt
```

Receiver:

```sh
cat </dev/tcp/my-domain-or-ip.com/9000 > myfile.txt
```

Remember: these commands only work while the server is running to relay the file.

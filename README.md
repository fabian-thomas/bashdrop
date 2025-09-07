# bashdrop

**bashdrop** is a tiny one-shot file transfer tool.

It was built for situations where you only have **bash** and raw TCP.
Especially, no way to use `scp`, `rsync`, `wormhole`, `croc`, `wget`, `curl`, or `netcat`.
Just bash and `/dev/tcp`.

A small Python server is required to **relay the file** between sender and receiver.
The server is set up fast and temporarily via SSH.
Optionally supports encryption via `openssl` if installed on the client devices.

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

### Run with `bashdrop`

The normal way is to start the server on a remote machine with:

```sh
bashdrop [-p PORT] <ssh-target> <public-domain-or-ip> [filename] [password]
```

This will copy `bashdrop-server.py` to the remote host (`/tmp/`) and run it there.
Example:

```sh
bashdrop user@myserver my-domain-or-ip.com
```

> [!IMPORTANT]
> The `<ssh-target>` and `<public-domain-or-ip>` must point to the **same machine**.
> - `<ssh-target>` → how you connect via SSH (e.g. `user@myserver`)
> - `<public-domain-or-ip>` → how sender/receiver connect (e.g. `my-domain-or-ip.com`)

### Run the server directly

If you are already on the target host, you can skip `bashdrop` and start the server manually:

```sh
bashdrop-server.py [-p PORT] <public-host-or-ip> [filename] [password]
```

### Transferring Files

The server prints ready-to-use **Sender** and **Receiver** commands in three modes:
1. Plain bash (`/dev/tcp`)
2. Plain + `sha256sum`
3. Encrypted (`openssl enc -aes-256-cbc -pbkdf2`) + `sha256sum`

Port `9000` is used by default.
Ensure port forwarding / firewall rules allow access.

- `-p PORT`: TCP port to listen on (default: `9000`).
- `filename`: filename shown in the copy-paste commands (default: `file`).
- `password`: optional, used only for the encrypted mode (default: random).

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

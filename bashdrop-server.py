#!/usr/bin/env python3
"""
bashdrop-server.py

A minimal one-shot relay (single TCP port; sequential upload → download).
The server just relays bytes once, then deletes the staged file and exits.

Three client modes are always printed:
  1) Plain Bash (/dev/tcp)
  2) Plain Bash + sha256sum
  3) Encrypted (openssl enc -aes-256-cbc -pbkdf2) + sha256sum

Usage:
  ./bashdrop-server.py <public-host-or-ip> [-p port] [filename] [password]

Defaults:
  - filename: "file"
  - password: random 10-char [A-Za-z0-9]
  - port: 9000
"""

import os
import sys
import socket
import tempfile
import secrets
import string
import shutil
import time
import argparse

# ----------------------------
# Tunables
# ----------------------------
DEFAULT_PORT = 9000
CHUNK_SIZE = 131072
PROBE_WAIT = 2.0  # seconds to decide if a connection is "real" (received data) vs. a stray probe

# ----------------------------
# ANSI colors
# ----------------------------
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
MAG    = "\033[35m"
CYAN   = "\033[36m"

BRIGHT_RED    = "\033[91m"
BRIGHT_GREEN  = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE   = "\033[94m"
BRIGHT_MAG    = "\033[95m"
BRIGHT_CYAN   = "\033[96m"
BRIGHT_WHITE  = "\033[97m"

# ----------------------------
# Helpers
# ----------------------------
def listen_once(port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(1)
    return s

def gen_password(n: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))

def term_width(default: int = 100) -> int:
    try:
        return max(60, shutil.get_terminal_size((default, 24)).columns)
    except Exception:
        return default

def hr(ch: str = "─", color: str = DIM, pad: int = 0) -> str:
    w = term_width()
    line = ch * max(10, w - pad)
    return f"{color}{line}{RESET}"

def box_title(text: str, color: str = BRIGHT_WHITE) -> None:
    w = term_width()
    label = f" {text} "
    side = max(0, (w - len(label) - 2) // 2)
    left = "─" * side
    right = "─" * side
    if len(left + label + right) < (w - 2):
        right += "─"
    print(f"{color}┌{left}{label}{right}┐{RESET}")

def box_footer(color: str = BRIGHT_WHITE) -> None:
    w = term_width()
    print(f"{color}└{'─' * (w - 2)}┘{RESET}")

def mode_header(name: str, color: str) -> None:
    print(f"{color}{BOLD}[{name}]{RESET}")

def cmd_block(cmd: str, color: str = BRIGHT_WHITE) -> None:
    print(hr("─", color=DIM))
    print(cmd)
    print(hr("─", color=DIM))

def info_kv(k: str, v: str, k_color: str = DIM, v_color: str = BRIGHT_WHITE) -> None:
    print(f"{k_color}{k}:{RESET} {v_color}{v}{RESET}")

def banner(pub: str, port: int, bname: str, password: str) -> None:
    box_title("One-shot relay — upload once → then download once", BRIGHT_GREEN)
    print(f"{DIM}This server accepts a single upload, then serves that exact content once for download and exits.{RESET}")
    print()
    info_kv("Public host/IP", pub)
    info_kv("Port", str(port))
    info_kv("Filename", bname)
    info_kv("Password (encrypted mode)", password)
    box_footer(BRIGHT_GREEN)
    print()

def _fn_cmd(body: str, pw: str, file_: str) -> str:
    return f"d(){{ {body} }}; d {pw} {file_}"

def print_sender_commands(pub: str, port: int, bname: str, password: str) -> None:
    box_title("Sender (SOURCE)", BRIGHT_BLUE)
    print(f"{DIM}Choose ONE mode and run exactly as shown (bash required for /dev/tcp).{RESET}\n")

    mode_header("Plain", RED)
    cmd_block(f"cat >/dev/tcp/{pub}/{port} < {bname}")
    cmd_block(f"bash -c 'cat >\"/dev/tcp/{pub}/{port}\" < \"$1\"' {password} {bname}")

    mode_header("Plain+sha256sum", BRIGHT_YELLOW)
    cmd_block(_fn_cmd(
        f'sha256sum "$2" && cat >"/dev/tcp/{pub}/{port}" <"$2";',
        password, bname
    ))
    cmd_block(
        f"bash -c 'f=\"$1\";sha256sum \"$f\"&&cat >\"/dev/tcp/{pub}/{port}\" < \"$f\"' {password} {bname}"
    )

    mode_header("Encrypted+sha256sum", BRIGHT_CYAN)
    cmd_block(_fn_cmd(
        f'sha256sum "$2" && openssl enc -aes-256-cbc -pbkdf2 -salt -pass pass:$1 <"$2" >\"/dev/tcp/{pub}/{port}\";',
        password, bname
    ))
    cmd_block(
        "bash -c '"
        "f=\"$1\";sha256sum \"$f\"&&"
        f"openssl enc -aes-256-cbc -pbkdf2 -salt -pass pass:\"$0\" < \"$f\" >\"/dev/tcp/{pub}/{port}\""
        f"' {password} {bname}"
    )

    box_footer(BRIGHT_BLUE)
    print()

def print_receiver_commands(pub: str, port: int, bname: str, password: str) -> None:
    box_title("Receiver (DESTINATION) — run AFTER upload completes", BRIGHT_MAG)
    print(f"{DIM}Again, choose ONE mode. Start these only after the sender finishes the upload step.{RESET}\n")

    mode_header("Plain", RED)
    cmd_block(f"cat </dev/tcp/{pub}/{port} > {bname}")
    cmd_block(f"bash -c 'cat <\"/dev/tcp/{pub}/{port}\" > \"$1\"' {password} {bname}")

    mode_header("Plain+sha256sum", BRIGHT_YELLOW)
    cmd_block(_fn_cmd(
        f'cat <"/dev/tcp/{pub}/{port}" >"$2" && sha256sum "$2";',
        password, bname
    ))
    cmd_block(
        f"bash -c 'f=\"$1\";cat <\"/dev/tcp/{pub}/{port}\" > \"$f\"&&sha256sum \"$f\"' {password} {bname}"
    )

    mode_header("Encrypted+sha256sum", BRIGHT_CYAN)
    cmd_block(_fn_cmd(
        f'openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:$1 <"/dev/tcp/{pub}/{port}" >"$2" && sha256sum "$2";',
        password, bname
    ))
    cmd_block(
        "bash -c '"
        f"f=\"$1\";openssl enc -d -aes-256-cbc -pbkdf2 -pass pass:\"$0\" < \"/dev/tcp/{pub}/{port}\" > \"$f\"&&sha256sum \"$f\""
        f"' {password} {bname}"
    )

    box_footer(BRIGHT_CYAN)
    print()

def accept_upload(staged_path: str, port: int) -> int:
    up_sock = listen_once(port)
    size = 0
    try:
        while True:
            conn, _ = up_sock.accept()
            try:
                conn.settimeout(PROBE_WAIT)
                try:
                    first_chunk = conn.recv(CHUNK_SIZE)
                except socket.timeout:
                    first_chunk = b""
                conn.settimeout(None)

                if not first_chunk:
                    conn.close()
                    continue

                with open(staged_path, "wb") as f:
                    f.write(first_chunk)
                    size += len(first_chunk)
                    while True:
                        data = conn.recv(CHUNK_SIZE)
                        if not data:
                            break
                        f.write(data)
                        size += len(data)
                conn.close()
                break
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                continue
    finally:
        try:
            up_sock.close()
        except Exception:
            pass
    return size

def serve_download(staged_path: str, port: int) -> None:
    down_sock = listen_once(port)
    try:
        conn, _ = down_sock.accept()
        with conn:
            with open(staged_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    conn.sendall(chunk)
            try:
                conn.shutdown(socket.SHUT_WR)
            except Exception:
                pass
    finally:
        try:
            down_sock.close()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(
        description="One-shot relay: upload once, then download once."
    )
    parser.add_argument("pub", help="Public host or IP")
    parser.add_argument("filename", nargs="?", default="file", help="Filename for file")
    parser.add_argument("password", nargs="?", help="Password for encrypted mode")
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_PORT, help="Port to listen on (default: 9000)")
    args = parser.parse_args()

    pub = args.pub
    bname = args.filename
    password = args.password if args.password else gen_password(10)
    port = args.port

    tmp_dir = tempfile.mkdtemp(prefix="bashdrop_stage_")
    staged_path = os.path.join(tmp_dir, "file")

    print()
    banner(pub, port, bname, password)

    print_sender_commands(pub, port, bname, password)
    print_receiver_commands(pub, port, bname, password)

    box_title("Waiting for upload…", BRIGHT_WHITE)
    print(f"{DIM}Listening on 0.0.0.0:{port}. The first client that sends data within ~{PROBE_WAIT:.0f}s will be treated as the sender.{RESET}")
    box_footer(BRIGHT_WHITE)
    t0 = time.time()
    try:
        size = accept_upload(staged_path, port)
        dt = time.time() - t0
        print(f"{BRIGHT_GREEN}Upload complete:{RESET} {size} bytes stored temporarily ({dt:.1f}s).")
    except KeyboardInterrupt:
        print(f"{BRIGHT_RED}Interrupted during upload. Exiting.{RESET}")
        try:
            os.remove(staged_path)
        except Exception:
            pass
        try:
            os.rmdir(tmp_dir)
        except Exception:
            pass
        sys.exit(130)

    print()
    box_title("Ready for download — start the receiver now", BRIGHT_WHITE)
    print(f"{DIM}Listening again on 0.0.0.0:{port}. The first client to read will receive the staged file once.{RESET}")
    box_footer(BRIGHT_WHITE)
    try:
        serve_download(staged_path, port)
        print(f"{BRIGHT_GREEN}Download complete.{RESET} Cleaning up.")
    except KeyboardInterrupt:
        print(f"{BRIGHT_RED}Interrupted during download. Cleaning up.{RESET}")

    try:
        os.remove(staged_path)
    except Exception:
        pass
    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass

    print(f"{BRIGHT_WHITE}Done.{RESET} File served once and removed.\n")

if __name__ == "__main__":
    main()

import re, socket, sys, time
# Usage: python3 -I mount_lx200.py Gr Gd GU   (sends :Gr# :Gd# :GU#, prints replies)
#        add --force to send a command on the refused list below.
HOST, PORT, WAIT = "192.168.0.1", 9999, 2.0
# Commands that reset or wipe the controller, change its serial speed, or overwrite stored data
# (OnStep command reference). Refused unless --force is given.
REFUSED = re.compile(r"^(ERESET|ENVRESET|SB\d|\$QZ!|LW.*|LL|L!|ESPFLASH)$")
def ask(cmd):
    with socket.create_connection((HOST, PORT), timeout=WAIT) as s:
        s.sendall((":" + cmd + "#").encode())
        buf, end = b"", time.time() + WAIT
        while b"#" not in buf and time.time() < end:
            try:
                chunk = s.recv(256)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
    return buf.decode(errors="replace").strip() or "<no reply>"
if __name__ == "__main__":
    force = "--force" in sys.argv[1:]
    for cmd in (a for a in sys.argv[1:] if a != "--force"):
        if REFUSED.match(cmd) and not force:
            print(":" + cmd + "# -> refused: resets or overwrites the controller. Add --force to send it anyway.")
            continue
        print(":" + cmd + "# -> " + ask(cmd))

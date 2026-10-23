import socket, sys, time
# Usage: python3 -I mount_lx200.py Gr Gd GU   (sends :Gr# :Gd# :GU#, prints replies)
HOST, PORT, WAIT = "192.168.0.1", 9999, 2.0
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
for cmd in sys.argv[1:]:
    print(":" + cmd + "# -> " + ask(cmd))

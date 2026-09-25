# Name: <your full name>   Student number: <your student number>
"""CMPT 371 Project 1 - HTTP/1.1 client on a raw TCP socket.

Usage: python3 client.py --host H --port P --path /a [--path /b] [--out FILE ...]
"""

import argparse
import socket
import sys


def parse_args(argv):
    """TASK 4. Parse --host (default 127.0.0.1), --port (int), --path
    (repeatable), --out (repeatable, paired with --path in order)."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1', help="host number", type=str)
    parser.add_argument('--port', required=True, help="port number", type=int)
    parser.add_argument('--path', required=True, action='append', help="path to request", type=str)
    parser.add_argument('--out', default=[], required=True, action='append', help="output file", type=str)
    args = parser.parse_args(argv)
    return args.host, args.port, args.path, args.out



def send_request(sock, host, path):
    """TASK 4. Send one GET request line, a Host header, and the blank line
    that ends it."""
    get_path = f"GET {path} HTTP/1.1\r\n"
    get_host = f"Host: {host}\r\n"
    request = get_path + get_host + "\r\n"
    sock.sendall(request.encode())



def read_head(sock, pending):
    """TASK 4. Read until the blank line ending the response head.
    Return (head_bytes, leftover) where leftover is body already received. The
    leftover is the start of the body and cannot be read again, so it must be
    counted toward Content-Length rather than discarded."""
    stop = b"\r\n\r\n"
    head_bytes = pending
    leftover = b""

    while(stop not in head_bytes):
        chunk = sock.recv(4096)
        if not chunk:
            return None
        head_bytes += chunk

    slice = head_bytes.find(b"\r\n\r\n")
    leftover = head_bytes[ slice + 4 : ]
    head_bytes = head_bytes[ : slice + 4]

    return (head_bytes, leftover)



def parse_head(head):
    """TASK 4. Split a response head into (status_code, reason, headers).
    headers is a dict with lower-cased names."""
    text = head.decode()
    lines = text.split("\r\n")
    status_line = lines[0]
    parts = status_line.split(" ", 2)

    if (len(parts) != 3):
        raise ValueError("malformed head line")
    status_code = int(parts[1])
    reason = parts[2]

    headers = {}
    for line in lines[1:]:
        if line == "":
            break 
        if ":" not in line:
            raise ValueError("malformed header line")
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()
    
    return status_code, reason, headers
    


def read_body(sock, length, pending):
    """TASK 4. Return exactly length body bytes, counting what is already in
    pending, plus any bytes left over past them. Do not read until the connection
    closes: the server keeps it open, so a read-to-EOF client never returns.
    Every check in task 4 runs against a server that holds the connection open
    for a full minute, so reading to EOF fails all four, not just the timing
    one."""
    data = pending
    leftover = b""

    while(len(data) < length):
        chunk = sock.recv(4096)
        if not chunk:
            return None
        data += chunk

    body_bytes = data[:length]
    leftover = data[length:]
    return body_bytes, leftover



def main(argv=None):
    """TASK 4. Connect once, then for each --path in turn: send the request,
    read the head, read exactly Content-Length bytes, print
    '<status> <reason> <n> bytes', and write the body to the matching --out file.
    Return 0 on success. All the paths travel over the one connection, so
    whatever is left in the buffer past one body is the start of the next
    response."""
    host, port, paths, outs = parse_args(argv)
    sock = socket.create_connection((host, port))
    pending = b""

    for i, e_path in enumerate(paths):
        e_out = outs[i]
        send_request(sock, host, e_path)

        result = read_head(sock, pending)
        if (result is None):
            print("connection closed before response head was received", file=sys.stderr)
            sock.close()    
            return 1
        head, pending = result 

        status_code, reason, headers = parse_head(head)
        length = int(headers["content-length"])

        result = read_body(sock, length, pending)
        if (result is None):
            print("connection closed before response body was received", file=sys.stderr)
            sock.close()
            return 1
        body, pending = result 

        print(f"{status_code} {reason} {len(body)} bytes")
        with open(e_out, "wb") as f:
            f.write(body)

        if (status_code != 200):
            break


    sock.close()
    return 0









if __name__ == "__main__":
    sys.exit(main())

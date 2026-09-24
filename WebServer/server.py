# Name: Eason Wang  Student number: 301618883
"""CMPT 371 Project 1 - static HTTP/1.1 server on raw TCP sockets.

Usage: python3 server.py --port PORT --root DIR [--workers N]
"""

import argparse
import mimetypes
import os
import queue
import socket
import sys
import threading
import time
from email.utils import formatdate

KNOWN_METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "TRACE", "CONNECT"}

requests_served = 0
counter_lock = threading.Lock()


def parse_args(argv):
    """TASK 1. Parse --port (int, 0 means pick any free port), --root
    (directory), --workers (int, how many threads the pool starts with,
    default 8). Accept --workers from task 1 even though nothing uses it until
    task 5: every command in the handout passes it."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True, help="port number", type=int)    
    parser.add_argument('--root', required=True, help="root directory", type=str)    
    parser.add_argument('--workers', default=8, help="number of workers", type=int)    
    args = parser.parse_args(argv)
    return args.port, args.root, args.workers



def recv_request_head(conn):
    """TASK 3. Call recv() repeatedly until the blank line that ends the header
    block has arrived. Return the head bytes including that blank line, or None
    if the client closed the connection first.
    In task 1 handle_connection may read the head with a single recv(); this is
    what replaces that call, and is where reading becomes correct."""
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        buffer += chunk
    return buffer



def parse_request(head):
    """TASK 3. Split a header block into (method, target, version, headers).
    headers is a dict with lower-cased names. Raise ValueError if the request
    line is not three fields or a header line has no colon; handle_request turns
    that into a 400."""
    text = head.decode()
    lines = text.split("\r\n")

    request_line = lines[0]
    parts = request_line.split(" ")
    if len(parts) != 3:
        raise ValueError("malformed request line")
    method, target, version = parts

    headers = {}
    for line in lines[1:]:
        if line == "":
            break  # the blank line ends the header block
        if ":" not in line:
            raise ValueError("malformed header line")
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    return method, target, version, headers



def resolve_path(root, target):
    """TASK 1. Turn a request target into an absolute path inside root: drop any
    query string, percent-decode, append index.html for a target ending in '/'.
    Return None if the target is malformed.
    All three rules are graded: /index.html?x=1 and /index.html are the same
    file, / is that directory's index.html, and /page/sub.html works."""
    remove_query = ""
    percent_decode = ""
    to_be_decoded = ""
    counter = 0

    if (len(target) <= 0):
        return None

    for char in target:
        if (char == '?'):
            break     
        remove_query = remove_query + char

    length = len(remove_query)
    while (length > counter):
        if (remove_query[counter] == '%'):
            if (counter + 2 >= length):
                return None            
             
            to_be_decoded = to_be_decoded + remove_query[counter + 1] 
            to_be_decoded = to_be_decoded + remove_query[counter + 2]

            if not all(c in "0123456789abcdefABCDEF" for c in to_be_decoded):
                return None

            char = chr(int(to_be_decoded, 16))
            percent_decode = percent_decode + char
            counter = counter + 3
            to_be_decoded = ""
            continue;

        percent_decode = percent_decode + remove_query[counter]
        counter = counter + 1         

    length = len(percent_decode)
    if (percent_decode[length-1] == '/'):
        percent_decode = percent_decode + "index.html"

    root_abs = os.path.abspath(root)
    if(percent_decode[0] == '/'):
        percent_decode = percent_decode[1:]
        final = os.path.abspath(os.path.join(root, percent_decode))
        if (final != root_abs and not final.startswith(root_abs + os.sep)):
            return None
        return final
    
    else:
        final = os.path.abspath(os.path.join(root, percent_decode))
        if (final != root_abs and not final.startswith(root_abs + os.sep)):
            return None
        return final



def build_response(status, reason, body, content_type, extra=None, include_body=True):
    """TASK 1. Return the full response as bytes: status line, the Date, Server,
    Content-Type, Content-Length and Connection headers, any extra headers,
    a blank line, then body.
    Every response goes through here, including 404, 400, 405 and 501, so every
    response carries all five headers. Content-Length is the number of body
    bytes that follow, and nothing else."""
    builder = ""
    http_response = f"HTTP/1.1 {status} {reason}\r\n"

    date = formatdate(usegmt=True)
    date_build = f"Date: {date}\r\n"

    server = f"Server: cmpt371/1.0\r\n"
    type_content = f"Content-Type: {content_type}\r\n"
    length_content = f"Content-Length: {len(body)}\r\n"
    connection = f"Connection: keep-alive\r\n"

    builder = http_response + date_build + server + type_content + length_content + connection 

    if extra:
        for name, value in extra.items():
            builder = builder + f"{name}: {value}\r\n"

    builder = builder + "\r\n"
    header_bytes = builder.encode("utf-8")
    return header_bytes + (body if include_body == True else b"")
        


def handle_request(head, root):
    """TASK 1, extended in tasks 2 and 3. Turn one header block into a complete
    response.
    Task 1: 200 and 404. Task 2: HEAD, which carries no body, and Content-Type
    from the file extension. Task 3: 400 (malformed request line or header line,
    no Host), 405 (POST and the other known methods, with Allow: GET, HEAD) and
    501 (a token that is not an HTTP method)."""
    try: 
        method, target, version, headers = parse_request(head)
    except ValueError:
        return build_response(400, "Bad Request", b"400 Bad Request\n", "text/html")

    if "host" not in headers:
        return build_response(400, "Bad Request", b"400 Bad Request\n", "text/html")

    if method not in KNOWN_METHODS:
        return build_response(501, "Not Implemented", b"Not Implemented\n", "text/html")
    
    if method not in ("GET", "HEAD"):
        return build_response(405, "Method Not Allowed", b"405 Method Not Allowed\n", "text/html", extra={"Allow": "GET, HEAD"})



    resolution_path = (resolve_path(root, target))

    if (resolution_path == None): #404 branch
        return build_response(404, "Not Found", b"404 Not Found\n", "text/html", include_body=(method != "HEAD"))
    elif(os.path.isfile(resolution_path) != True): #missing 404 branch
        return build_response(404, "Not Found", b"404 Not Found\n", "text/html", include_body=(method!="HEAD"))

    else: #200 branch
        content_type = mimetypes.guess_type(resolution_path)[0]
        if (content_type is None):
            content_type = "application/octet-stream"

        if (method == "GET"):
            with open(resolution_path, "rb") as f:
                body = f.read()
            return build_response(200, "OK", body, content_type, include_body=True)
        if (method == "HEAD"):
            with open(resolution_path, "rb") as f:
                body = f.read()
            return build_response(200, "OK", body, content_type, include_body=False)




def handle_connection(conn, root):
    """TASK 1, extended in tasks 3 and 5. Serve requests on one connection until
    the client closes it or it goes idle -- a few seconds; five is reasonable.
    Task 1: read the head (one recv() is enough for now), call handle_request,
    sendall() the response, and loop. Task 3: replace that read with
    recv_request_head. Task 5: after each response, increment requests_served
    under counter_lock and print 'served <n>' to stderr, where n is the value
    this request produced, read inside the same lock that incremented it."""
    while True:
        head = conn.recv(4096)
        if not head:
            break

        response = handle_request(head, root)
        conn.sendall(response)

    conn.close()



def worker(work_queue, root):
    """TASK 5. Take accepted connections off work_queue and serve them, forever.
    Every worker thread runs this; none of them is created per connection.
    Nothing before task 5 calls this, and main must not start any worker threads
    until you write it."""
    raise NotImplementedError



def main(argv=None):
    """TASK 1, replaced in task 5. Bind 127.0.0.1 on the requested port, listen,
    print the port line below, then serve connections.
    Task 1: accept one connection at a time and pass each to handle_connection.
    Task 5: replace that loop -- create --workers threads running worker() and a
    queue.Queue, and let main do nothing but accept and enqueue."""
    # Given. The grading script reads this line to find your server, so print it
    # exactly as written, immediately after listen(), and keep flush=True.
    #     print("Listening on port %d" % listener.getsockname()[1], flush=True)
    port, root, workers = parse_args(argv)

    listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen.bind(("127.0.0.1", port))
    listen.listen()

    print("Listening on port %d" % listen.getsockname()[1], flush=True)

    try:
        while True:
            conn, addr = listen.accept()
            handle_connection(conn, root)
    finally:
        listen.close()

    
if __name__ == "__main__":
    main()

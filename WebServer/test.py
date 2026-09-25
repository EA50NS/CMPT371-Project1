from email.utils import formatdate
import os

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




def handle_request(head, root):
    lines = head.decode(); 
    full_split = lines.split("\r\n")
    line_1 = full_split[0]
    line_1_split = line_1.split(" ")
    target = line_1_split[1]

    resolved_path = (resolve_path(root, target))

    if (resolved_path == None): #404 branch
        return build_response(404, "Not Found", b"404 Not Found", "text/html")

    elif(os.path.isfile(resolved_path) != True): #missing 404 branch
        return build_response(404, "Not Found", b"404 Not Found", "text/html")

    else: #200 branch
        with open(resolved_path, "rb") as f:
            body = f.read()
        return build_response(200, "OK", body,"text/html")




def build_response(status, reason, body, content_type, extra=None):
    builder = ""
    http_response = f"HTTP/1.1 {status} {reason}\r\n"

    date = formatdate(usegmt=True)
    date_build = f"Date: {date}\r\n"

    server = f"Server: cmpt371/1.0\r\n"
    type_content = f"Content-Type: {content_type}\r\n"
    length_content = f"Content-Length: {len(body)}\r\n"
    connection = f"Connection: keep-alive\r\n\r\n"
    
    builder = http_response + date_build + server + type_content + length_content + connection 
    header_bytes = builder.encode("utf-8")
    return header_bytes + body

body = b"<html><body><h1>CMPT 371</h1></body></html>"
bytes = (build_response(200, "BAD", body, "text/html"))


request = b"GET /.html HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
print(handle_request(request, "www").decode())



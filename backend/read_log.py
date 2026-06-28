import codecs

try:
    with codecs.open('server.log', 'r', 'utf-16') as f:
        content = f.read()
    with codecs.open('server_utf8.log', 'w', 'utf-8') as f:
        f.write(content)
    print("Success")
except Exception as e:
    with open('error.txt', 'w') as f:
        f.write(str(e))

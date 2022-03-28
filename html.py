"""
> http -f POST https://kbdlayout.info/viewer submit="view it" file@en-GB-t-k0-linux-colemak.xml
> http -f POST https://kbdlayout.info/viewer file@en-GB-t-k0-linux-colemak.xml

HTTP/1.1 302 Found
Content-Length: 0
Date: Mon, 28 Mar 2022 19:57:47 GMT
Location: /6cce0d94-5ac1-4ce2-9c11-2905e930f1a6
Server: Kestrel
X-Content-Type-Options: nosniff
"""

# https://kbdlayout.info/6cce0d94-5ac1-4ce2-9c11-2905e930f1a6/download/html

from lxml import etree
import sys
import requests

for path in sys.argv[1:]:
    print(path)
    xml = etree.parse(path, etree.XMLParser(dtd_validation=True))
    name = xml.findall("names/name")[-1].attrib['value']
    response = requests.post("https://kbdlayout.info/viewer", files = {'file': open(path)})
    assert response.ok
    url = response.url + "/download/html"
    response2 = requests.get(url)
    assert response2.ok
    with open("html/" + name + ".html", 'wb') as f:
        f.write(response2.content)
    continue
import lxml.html as html
import lxml.etree as etree
from tornado.httpclient import AsyncHTTPClient
from hashlib import sha1
import mimetypes
from tornado.ioloop import IOLoop

AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")

def sitemap(path='sitemap.xml'):
    tree = etree.parse(open(path, 'r'))
    return tree.xpath(
        '//sitemap:loc/text()',
        namespaces={'sitemap':'http://www.sitemaps.org/schemas/sitemap/0.9'})

def get_image(product_page):
    tree = html.document_fromstring(product_page.body)
    tags = tree.xpath('//p[@class="product-image"]/img/@src')
    return tags[0]

crawl_queue = []
running_reqs = 0

class Request(object):

    def __init__(self):
        global running_reqs
        try:
            self.page_url = crawl_queue.pop()
        except IndexError:
            return
        print '> %s' % self.page_url
        running_reqs += 1
        AsyncHTTPClient().fetch(self.page_url, self.got_url)

    def got_url(self, page):
        try:
            self.image_url = get_image(page)
        except IndexError:
            self.finish()
            return
        print self.image_url
        AsyncHTTPClient().fetch(self.image_url, self.got_image)

    def got_image(self, response):
        data = response.body
        basename = sha1(response.body).hexdigest()
        mime = response.headers.get('Content-Type', 'image/jpeg')
        suffix = mimetypes.guess_extension(mime)
        open('images/%s%s' % (basename, suffix), 'w').write(response.body)
        self.finish()

    def finish(self):
        global running_reqs
        running_reqs -= 1
        if running_reqs < 200 and len(crawl_queue) > 0:
            Request()
        print '< %s' % self.page_url


def run():
    crawl_queue.extend(sitemap())
    for i in xrange(10):
        Request()
    IOLoop.instance().start()

if __name__ == '__main__':
    run()

from cStringIO import StringIO
import segment as s
import tornado.ioloop as ioloop
import tornado.web as web

fnames, vectors = s.load_vectors('images')

class QuiltHandler(web.RequestHandler):

    def post(self):
        data = StringIO(self.request.body)
        seg = s.Segmentation(data)
        seg.apply_textures(vectors, fnames)
        result = StringIO()
        seg.to_pil().save(result, format='PNG')
        result.seek(0)
        self.set_status(200)
        self.set_header('Content-Type', 'image/png')
        self.write(result.getvalue())

app = web.Application([
    ('/quilt', QuiltHandler)
])

if __name__ == '__main__':
    import sys
    try:
        port = int(sys.argv[1])
    except:
        print 'invalid port. port number should be supplied as first argument'
        sys.exit(1)
    print port
    app.listen(port)
    ioloop.IOLoop.current().start()

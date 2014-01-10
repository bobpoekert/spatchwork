from PIL import Image
import glob

for inf in glob.glob('images/*.jpe*'):
    print inf
    img = Image.open(inf)
    crop = img.crop((40, 0, 400, 325))
    basename = inf.split('.')[0]
    crop.save('%s_cropped.jpeg' % basename)

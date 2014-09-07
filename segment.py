from skimage import io, color, transform
import numpy as np
import numpy.ma as ma
import scipy.spatial.distance as distance
from skimage.segmentation import felzenszwalb
from skimage.util import img_as_float
from glob import glob
from functools import partial
import json, time, random

io.use_plugin('pil')

norm_cache = {}
def norms(mat):
    try:
        return norm_cache[id(mat)]
    except KeyError:
        res = np.apply_along_axis(distance.norm, axis=1, arr=mat)
        norm_cache[id(mat)] = res
        return res

class Segmentation(object):

    def __init__(self, fname):
        self.fname = fname
        self.image_cache = {}

        print 'loading image'
        self.raw_img = io.imread(fname)
        self._segment_ids = None
        img_float = img_as_float(self.raw_img)
        print 'segmenting image'
        self.segments = felzenszwalb(img_float, scale=300, sigma=0.5, min_size=100)

    def load_image(self, fname, shape):
        key = (fname, shape)
        if key in self.image_cache:
            return self.image_cache[key]
        texture = io.imread(fname)
        #texture = transform.resize(texture, (shape[0], shape[1], texture.shape[2]))
        texture = np.resize(texture, (shape[0], shape[1], texture.shape[2]))
        #texture.resize((shape[0], shape[1], texture.shape[2]))
        ks = self.image_cache.keys()
        if len(ks) > 100:
            del self.image_cache[ks[0]]
        self.image_cache[key] = texture
        return texture

    def segment_mask(self, segment_id):
        mask = np.empty(self.segments.shape)
        mask.fill(segment_id)
        return np.equal(self.segments, mask)

    def segment_ids(self):
        if not self._segment_ids:
            self._segment_ids = np.unique(self.segments)
        return self._segment_ids

    def __iter__(self):
        for id in self.segment_ids():
            yield self.segment_img_data(id)

    def apply_textures(self, vectors, fnames):
        ids = self.segment_ids()
        count = ids.shape[0]
        done = 0
        for segment_id in ids:
            print float(done) / count * 100
            done += 1
            mask = self.segment_mask(segment_id)
            vector = feature_vector(self.raw_img[np.nonzero(mask)])

            #distances = np.sqrt(np.sum((vectors - vector)**2, axis=1)) # euclidian
            #distances = np.apply_along_axis(partial(distance.cosine, vector), axis=1, arr=vectors) # cosine

            # compute cosine similarity
            dots = np.einsum('ij,ij->i', vectors, np.resize(vector, vectors.shape))
            v_norm = np.resize(distance.norm(vector), vectors.shape[0])
            m_norm = norms(vectors)
            scales = v_norm * m_norm
            similarities = dots / scales

            idx = np.argmax(similarities)
            fname = fnames[idx]
            texture = self.load_image(fname, mask.shape)
            self.raw_img[mask] = texture[mask]

    def show(self):
        io.imshow(self.raw_img)

    def save(self, fname):
        io.imsave(fname, self.raw_img)

def feature_vector(image):
    hist, edges = np.histogram(image, bins=256)
    #total = np.sum(hist)
    return hist

def vectors_from_images(fnames):
    vectors = []
    for fname in fnames:
        print fname
        img = io.imread(fname)
        vec = feature_vector(img)
        vectors.append(vec)
    return np.array(vectors)

def save_vectors(folder, fnames, vectors):
    with open('%s/fnames.json' % folder, 'w') as f:
        json.dump(fnames, f)
    np.save('%s/vectors.npy' % folder, vectors)

def load_vectors(folder):
    with open('%s/fnames.json' % folder, 'r') as f:
        fnames = json.load(f)
    vecs = np.load('%s/vectors.npy' % folder)
    return (fnames, vecs)

def build_dataset(folder):
    names = glob('%s/*.jpeg' % folder)
    vectors = vectors_from_images(names)
    save_vectors(folder, names, vectors)

if __name__ == '__main__':
    import sys
    #build_dataset('images')
    print 'loading corpus'
    fnames, vectors = load_vectors('images')
    for target in glob('targets/*'):
        if target.endswith('_processed.png'):
            continue
        print target
        seg = Segmentation(target)
        print 'applying textures'
        seg.apply_textures(vectors, fnames)
        seg.save('%s_processed.png' % target.split('.')[0])

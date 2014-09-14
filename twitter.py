import segment as s
import keys
import sqlite3
import time, urllib, traceback, tempfile, os, re
from cStringIO import StringIO
import tweepy

auth = tweepy.OAuthHandler(keys.twitter.api_key, keys.twitter.api_secret)
auth.set_access_token(keys.twitter.access_token, keys.twitter.access_secret)
twitter = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

def get_mentions(poll_interval=60, direct_mentions_only=True, last_mention=None):
    #screen_name = twitter.me().screen_name
    screen_name = 'a_quilt_bot'
    print screen_name
    last_checked = 0
    print last_mention
    while 1:
        print 'checking'
        current_mentions = twitter.mentions_timeline(since_id=last_mention, count=100)
        last_checked = time.time()
        if not current_mentions:
            print 'no mentions :('
            time.sleep(poll_interval)
            continue
        if direct_mentions_only:
            current_mentions = [t for t in current_mentions if \
                    re.split('[^@\w]', t.text)[0] == '@' + screen_name]
        if current_mentions: 
            last_mention = current_mentions[0].id
            for mention in current_mentions:
                yield mention
        time.sleep(poll_interval)

db = sqlite3.connect('twitter.sqlite')

def init_db():
    c = db.cursor()
    c.execute('create table mentions (mention_id text unique not null, reply_id text, processed boolean, started_on integer, finished_on integer)')
    c.execute('create index mid on mentions (mention_id)')
    db.commit()
    c.close()

def was_processed(tweet_id):
    c = db.cursor()
    c.execute('select * from mentions where mention_id = ? and processed = 1 limit 1',
            (tweet_id,))
    row = c.fetchone()
    if not row:
        return False
    processed = row[2]
    c.close()
    return bool(processed)

def record_tweet_processing(mention_id=None):
    assert mention_id is not None
    c = db.cursor()
    c.execute('select * from mentions where mention_id = ?', (mention_id,))
    if c.fetchone():
        c.close()
        return
    c.execute('insert into mentions (mention_id, processed, started_on) values (?, 0, ?)',
        (mention_id, int(time.time())))
    db.commit()
    c.close()

def record_tweet_processed(mention_id=None, reply_id=None):
    assert mention_id
    assert reply_id
    print mention_id, reply_id
    c = db.cursor()
    c.execute('update mentions set processed = 1, reply_id = ?, finished_on = ? where mention_id = ?',
        (reply_id, int(time.time()), mention_id))
    db.commit()
    c.close()

def last_mention_id():
    c = db.cursor()
    c.execute('select mention_id from mentions where processed = 1 order by finished_on desc limit 1')
    res = c.fetchone()
    c.close()
    if res:
        return res[0]

def get_images(tweet):
    for media in tweet._json.get('entities', []).get('media', []):
        print media
        if not media:
            continue
        for obj in media:
            if media.get('type') == 'photo':
                yield media['media_url']

fnames, vectors = s.load_vectors('images')

def process_image(inp_url):
    print 'downloading %s' % inp_url
    data = urllib.urlopen(inp_url).read()
    print 'downloaded'
    seg = s.Segmentation(StringIO(data))
    seg.apply_textures(vectors, fnames)
    return seg.to_pil()

def process_mention(image_url, _id, sender):
    print image_url, _id, sender
    record_tweet_processing(mention_id=_id)
    blob = StringIO()
    process_image(image_url).save(blob, format='JPEG')
    blob.seek(0)
    res = twitter.update_with_media(
            'not-actually-a-file.jpeg', # this is kind of gross
            file=blob,
            in_reply_to_status_id=_id,
            status=u'\u2766@%s ' % sender)
    record_tweet_processed(
        mention_id=_id,
        reply_id=res.id)

if __name__ == '__main__':
    for mention in get_mentions():
        try:
            mid = mention.id
            print mid
            if was_processed(mid):
                continue
            sender = mention.user.screen_name
            try:
                image = next(get_images(mention))
            except:
                continue
            process_mention(image, mid, sender)
        except:
            traceback.print_exc()

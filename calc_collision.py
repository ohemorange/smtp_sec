import hashcash

def sha512_512k(data):
    #
    # This abuse of sha512 forces it to work with at least 512kB of data,
    # no matter what it started with. On each iteration, we add one
    # hexdigest to the front of the string (to prevent reuse of state).
    # Each hexdigest is 128 bytes, so that gives:
    #
    # Total == 128 * (0 + 1 + 2 + ... + 90) + 128 == 128 * 4096 == 524288
    #
    # Max memory use is sadly only 10KB or so - hardly memory-hard. :-)
    # Oh well!  I'm no cryptographer, and yes, we should probably just
    # be using scrypt.
    #
    sha512 = hashlib.sha512
    for i in range(0, 91):
        data = sha512(data).hexdigest() + data
    return sha512(data).hexdigest()

def command(a, b):
    bits, challenge = int(a), b
    expected = 2 ** bits
    def marker(counter):
        progress = ((1024.0 * counter) / expected) * 100
    collision = sha512_512kCollide(challenge, bits, callback1k=marker)
    print challenge
    print collision
    print self._success({
        'challenge': challenge,
        'collision': collision
    })
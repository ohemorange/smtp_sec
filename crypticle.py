# PyCrypto-based authenticated symetric encryption
# from http://snipperize.todayclose.com/snippet/py/Authenticated-encryption-with-PyCrypto--122005/
import cPickle as pickle
import hashlib
import hmac
from Crypto.Cipher import AES
from Crypto.Util.randpool import RandomPool

AES_BLOCK_SIZE = 16
SIG_SIZE = hashlib.sha256().digest_size

class AuthenticationError(Exception): pass

class Crypticle(object):
    """Authenticated encryption class
    
    Encryption algorithm: AES-CBC
    Signing algorithm: HMAC-SHA256
    """

    PICKLE_PAD = "pickle::"

    def __init__(self, key_string):
        self.keys = self.extract_keys(key_string)

    @classmethod
    # don't use this
    def generate_key_string(cls, key_size=256):
        key = RandomPool(512).get_bytes(key_size / 8 + SIG_SIZE)
        return key

    @classmethod
    def extract_keys(cls, key_string):
        # key = key_string.decode("base64")
        # if len(key) != key_size / 8 + SIG_SIZE:
        #     print "invalid key"
        return key_string[:-SIG_SIZE], key_string[-SIG_SIZE:]

    def encrypt(self, data):
        """encrypt data with AES-CBC and sign it with HMAC-SHA256"""
        aes_key, hmac_key = self.keys
        pad = AES_BLOCK_SIZE - len(data) % AES_BLOCK_SIZE
        data = data + pad * chr(pad)
        iv_bytes = RandomPool(512).get_bytes(AES_BLOCK_SIZE)
        cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
        data = iv_bytes + cypher.encrypt(data)
        sig = hmac.new(hmac_key, data, hashlib.sha256).digest()
        return data + sig

    def decrypt(self, data):
        print "decrypt data", data
        """verify HMAC-SHA256 signature and decrypt data with AES-CBC"""
        aes_key, hmac_key = self.keys
        sig = data[-SIG_SIZE:]
        data = data[:-SIG_SIZE]
        if hmac.new(hmac_key, data, hashlib.sha256).digest() != sig:
            print "decryption failed"
            return None
            #raise AuthenticationError("message authentication failed")
        iv_bytes = data[:AES_BLOCK_SIZE]
        data = data[AES_BLOCK_SIZE:]
        cypher = AES.new(aes_key, AES.MODE_CBC, iv_bytes)
        data = cypher.decrypt(data)
        return data[:-ord(data[-1])]

    def dumps(self, obj, pickler=pickle):
        """pickle and encrypt a python object"""
        return (self.encrypt(self.PICKLE_PAD + pickler.dumps(obj))).encode("hex")

    def loads(self, data, pickler=pickle):
        print "called loads", data
        """decrypt and unpickle a python object"""
        data = self.decrypt(data.decode("hex"))
        print "loads data", data
        # simple integrity check to verify that we got meaningful data
        assert data.startswith(self.PICKLE_PAD), "unexpected header"
        return pickler.loads(data[len(self.PICKLE_PAD):])


# if __name__ == "__main__":
#     # usage example
#     key = Crypticle.generate_key_string()
#     data = {"dict": "full", "of": "secrets"}
#     crypt = Crypticle(key)
#     safe = crypt.dumps(data)
#     assert data == crypt.loads(safe)
#     print "encrypted data:"
#     print safe.encode("base64")
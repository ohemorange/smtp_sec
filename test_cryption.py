import scrypt
from crypticle import Crypticle
pp = "secret"
random = str(272478237)
s = scrypt.hash(pp, random)
c = Crypticle(s)
data = "meow meow meow"
c.dumps(data)
c.loads(c.dumps(data))

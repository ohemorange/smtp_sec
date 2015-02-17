class original(object):
	def __init__(self):
		print "boop"

	def hi(self):
		print "hi"
	def yo(self):
		self.hi()
		print "yo"
	def sup(self):
		print "namuch"

class second(original):
	pass
	def __init__(self):
		super(second, self).__init__()
		print "beep"

	def hi(self):
		print "hello"

a = original()
a.hi()
a.yo()

b = second()
b.hi()
b.yo()
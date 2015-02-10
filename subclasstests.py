class original():
	def hi(self):
		print "hi"
	def yo(self):
		self.hi()
		print "yo"
	def sup(self):
		print "namuch"

class second(original):
	pass
	def hi(self):
		print "hello"

a = original()
a.hi()
a.yo()

b = second()
b.hi()
b.yo()
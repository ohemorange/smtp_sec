import subclasstests

class original(subclasstests.original):
	pass
	def hi(self):
		print "heya"
	def yo(self):
		print "oy"

a = original()
a.hi()

class second(subclasstests.second):
	pass

b = second()
b.yo()

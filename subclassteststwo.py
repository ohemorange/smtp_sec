import subclasstests

class original(subclasstests.original):
	pass
	def hi(self):
		print "heya"
	def yo(self):
		print "oy"
	def sup(self):
		return subclasstests.original.sup(self)

a = original()
a.hi()
a.sup()

class second(subclasstests.second):
	pass

b = second()
b.yo()

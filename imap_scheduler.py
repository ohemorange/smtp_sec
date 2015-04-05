# Takes information about the state of metadata-secure messages
# that have been received to a client, and outputs a schedule for
# pushing messages up and pulling messages down from the imap
# server.
#
# Leaks one bit of information (pull or push) every time interval dt

class ImapScheduler:
	def __init__(self):
		self.received_messages = 0
		self.want_to_delete_messages = 0
		self.pushed_messages = 0
		self.pulled_messages = 0

	def received_message(self):
		self.received_messages += 1

	def want_to_delete_message(self):
		self.want_to_delete_messages += 1

	# return True for push, False for pull
	# TODO
	def next_time_point_action_is_push(self):
		return True

	def message_was_pushed(self):
		self.pushed_messages += 1

	def message_was_pulled(self):
		self.pulled_messages += 1

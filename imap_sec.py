import imaplib

class IMAP4(imaplib.IMAP4):
	pass
	# override/add here
	def __init__(self):
		raise NotImplementedError("Do not use this class")

# we need to keep track of imap state
class IMAP4_SSL(imaplib.IMAP4_SSL):
	pass

	# places all metadata into message
	# replaces with fake metadata
	# calls super to append to cryptoblobs mailbox
	# updates index
	def append(self, mailbox, flags, date_time, message):
		return imaplib.IMAP4_SSL.append(mailbox, \
			flags, date_time, message)

	# update index
	def copy(self, message_set, new_mailbox):
		return imaplib.IMAP4_SSL.copy(message_set, new_mailbox)

	# update index
	def create(self, mailbox):
		return imaplib.IMAP4_SSL.create(mailbox)

	# update index
	def delete(self, mailbox):
		return imaplib.IMAP4_SSL.delete(mailbox)

	# update index
	def deleteacl(self, mailbox, who):
		return imaplib.IMAP4_SSL.deleteacl(mailbox, who)

	# update index
	def list(self, directory=directory, pattern=pattern):
		return imaplib.IMAP4_SSL.list(directory, pattern)

	def logout(self):
		return imaplib.IMAP4_SSL.logout()

	def lsub(self, directory=directory, pattern=pattern):
		return imaplib.IMAP4_SSL.lsub(directory, pattern)

	def myrights(self, mailbox):
		return imaplib.IMAP4_SSL.myrights(mailbox)

	def noop(self):
		return imaplib.IMAP4_SSL.noop()

	def recent(self):
		return imaplib.IMAP4_SSL.recent()

	def rename(self, oldmailbox, newmailbox):
		return imaplib.IMAP4_SSL.rename(oldmailbox, newmailbox)

	def search(self, charset, *criteria):
		return imaplib.IMAP4_SSL.search(charset, criteria)

	def select(self, mailbox=mailbox, readonly=readonly):
		return imaplib.IMAP4_SSL.select(mailbox, readonly)

	def sort(self, sort_criteria, charset, *search_criteria):
		return imaplib.IMAP4_SSL.sort(sort_criteria, charset, search_criteria)

	def status(self, mailbox, names):
		return imaplib.IMAP4_SSL.status(mailbox, names)

	def subscribe(self, mailbox):
		return imaplib.IMAP4_SSL.subscribe(mailbox)

	def thread(self, threading_algorithm, charset, *search_criteria):
		return imaplib.IMAP4_SSL.thread(threading_algorithm, charset, search_criteria)

	def unsubscribe(self, mailbox):
		return imaplib.IMAP4_SSL.unsubscribe(mailbox)


class IMAP4_stream(imaplib.IMAP4_stream):
	pass

	def __init__(self):
		raise NotImplementedError("Do not use this class")


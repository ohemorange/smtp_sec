import imaplib

class IMAP4(imaplib.IMAP4):
	pass
	# override/add here
	def __init__(self):
		raise NotImplementedError("Do not use this class")

CRLF = imaplib.CRLF

# we need to keep track of imap state
class IMAP4_SSL(imaplib.IMAP4_SSL):
	pass

	# places all metadata into message
	# replaces with fake metadata
	# calls super to append to cryptoblobs mailbox
	# updates index
	def append(self, mailbox, flags, date_time, message):
		return imaplib.IMAP4_SSL.append(self, mailbox, \
			flags, date_time, message)

	# update index
	def copy(self, message_set, new_mailbox):
		return imaplib.IMAP4_SSL.copy(self, message_set, new_mailbox)

	# update index
	def create(self, mailbox):
		return imaplib.IMAP4_SSL.create(self, mailbox)

	# update index
	def delete(self, mailbox):
		return imaplib.IMAP4_SSL.delete(self, mailbox)

	# update index
	def deleteacl(self, mailbox, who):
		return imaplib.IMAP4_SSL.deleteacl(self, mailbox, who)

	# update index
	def list(self, directory='""', pattern='*'):
		return imaplib.IMAP4_SSL.list(self, directory, pattern)

	def logout(self):
		return imaplib.IMAP4_SSL.logout(self)

	def lsub(self, directory='""', pattern='*'):
		return imaplib.IMAP4_SSL.lsub(self, directory, pattern)

	def myrights(self, mailbox):
		return imaplib.IMAP4_SSL.myrights(self, mailbox)

	def noop(self):
		return imaplib.IMAP4_SSL.noop(self)

	def recent(self):
		return imaplib.IMAP4_SSL.recent(self)

	def rename(self, oldmailbox, newmailbox):
		return imaplib.IMAP4_SSL.rename(self, oldmailbox, newmailbox)

	def search(self, charset, *criteria):
		return imaplib.IMAP4_SSL.search(self, charset, criteria)

	def select(self, mailbox='INBOX', readonly=False):
		return imaplib.IMAP4_SSL.select(self, mailbox, readonly)

	def sort(self, sort_criteria, charset, *search_criteria):
		return imaplib.IMAP4_SSL.sort(self, sort_criteria, charset, search_criteria)

	def status(self, mailbox, names):
		return imaplib.IMAP4_SSL.status(self, mailbox, names)

	def subscribe(self, mailbox):
		return imaplib.IMAP4_SSL.subscribe(self, mailbox)

	def thread(self, threading_algorithm, charset, *search_criteria):
		return imaplib.IMAP4_SSL.thread(self, threading_algorithm, charset, search_criteria)

	def unsubscribe(self, mailbox):
		return imaplib.IMAP4_SSL.unsubscribe(self, mailbox)


class IMAP4_stream(imaplib.IMAP4_stream):
	pass

	def __init__(self):
		raise NotImplementedError("Do not use this class")


import imaplib, time

class IMAP4(imaplib.IMAP4):
    pass
    # override/add here
    def __init__(self):
        raise NotImplementedError("Do not use this class")

CRLF = imaplib.CRLF

# we need to keep track of imap state
class IMAP4_SSL(imaplib.IMAP4_SSL):
    pass

    # ********************************************************** #
    # the follow methods are called by mailpile
    # ********************************************************** #

    def list(self, directory='""', pattern='*'):
        typ, data = imaplib.IMAP4_SSL.list(self, directory, pattern)
        print "list", data
        return typ, data

    def noop(self):
        typ, data = imaplib.IMAP4_SSL.noop(self)
        # print "noop", data
        return typ, data

    # switches which mailbox we're prodding for updates in
    def select(self, mailbox='INBOX', readonly=False):
        typ, data = imaplib.IMAP4_SSL.select(self, mailbox, readonly)
        print "select", mailbox, data
        return typ, data

    # asks for and receives email
    # command=SEARCH returns a list of the uids in the current mailbox
    # command=FETCH fetches a specific message?
    # it can also be SORT and THREAD.
    def uid(self, command, *args):
        a = imaplib.IMAP4_SSL.uid(self, command, *args)
        print "uid", command, a
        return a

    # ******************************************************** #
    # these methods are like maybe called but less important? 


    def store(self, message_set, command, flags):
        a = imaplib.IMAP4_SSL.store(self, message_set, command, flags)
        print "store", a
        return a

    # def open():

    def fetch(self, message_set, message_parts):
        a = imaplib.IMAP4_SSL.fetch(self, message_set, message_parts)
        print "fetch", data
        return a

    def capability(self):
        typ, data = imaplib.IMAP4_SSL.capability(self)
        # print "capability", data
        return typ, data

    def login(self, user, password):
        typ, data = imaplib.IMAP4_SSL.login(self, user, password)
        # print "login", data
        return typ, data

    def search(self, charset, *criteria):
        a = imaplib.IMAP4_SSL.search(self, charset, *criteria)
        print "search", a
        return a

    # places all metadata into message
    # replaces with fake metadata
    # calls super to append to cryptoblobs mailbox
    # updates index
    # this will probably not be called.
    def append(self, mailbox, flags, date_time, message):
        typ, data = imaplib.IMAP4_SSL.append(self, mailbox, \
            flags, date_time, message)
        print "append", data
        return typ, data

    # ********************************************************* #

    def _get_tagged_response(self, tag):
        a = imaplib.IMAP4_SSL._get_tagged_response(self, tag)
        # print "tag resp", a
        return a

    def readline(self):
        a = imaplib.IMAP4_SSL.readline(self)
        # print "readline", a
        return a

    # update index
    def copy(self, message_set, new_mailbox):
        return imaplib.IMAP4_SSL.copy(self, message_set, new_mailbox)

    # update index
    def create(self, mailbox):
        typ, data = imaplib.IMAP4_SSL.create(self, mailbox)
        print "create", data
        return typ, data

    # update index
    def delete(self, mailbox):
        return imaplib.IMAP4_SSL.delete(self, mailbox)

    # update index
    def deleteacl(self, mailbox, who):
        return imaplib.IMAP4_SSL.deleteacl(self, mailbox, who)

    def logout(self):
        return imaplib.IMAP4_SSL.logout(self)

    def lsub(self, directory='""', pattern='*'):
        return imaplib.IMAP4_SSL.lsub(self, directory, pattern)

    def myrights(self, mailbox):
        return imaplib.IMAP4_SSL.myrights(self, mailbox)

    def recent(self):
        typ, data = imaplib.IMAP4_SSL.recent(self)
        print "recent", data
        return typ, data

    def rename(self, oldmailbox, newmailbox):
        return imaplib.IMAP4_SSL.rename(self, oldmailbox, newmailbox)

    def search(self, charset, *criteria):
        return imaplib.IMAP4_SSL.search(self, charset, criteria)

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


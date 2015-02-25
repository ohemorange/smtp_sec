import imaplib, time
import re
from mailbox import Message
import json
import sys
import traceback

class IMAP4(imaplib.IMAP4):
    pass
    # override/add here
    def __init__(self):
        raise NotImplementedError("Do not use this class")

CRLF = imaplib.CRLF

# ***************************************************************
# parsing code from mailpile

IMAP_TOKEN = re.compile('("[^"]*"'
                        '|[\\(\\)]'
                        '|[^\\(\\)"\\s]+'
                        '|\\s+)')

def _parse_imap(reply):
    """
    This routine will parse common IMAP4 responses into Pythonic data
    structures.

    >>> _parse_imap(('OK', ['One (Two (Th ree)) "Four Five"']))
    (True, ['One', ['Two', ['Th', 'ree']], 'Four Five'])

    >>> _parse_imap(('BAD', ['Sorry']))
    (False, ['Sorry'])
    """
    stack = []
    pdata = []
    for dline in reply[1]:
        while True:
            if isinstance(dline, (str, unicode)):
                m = IMAP_TOKEN.match(dline)
            else:
                print 'WARNING: Unparsed IMAP response data: %s' % (dline,)
                m = None
            if m:
                token = m.group(0)
                dline = dline[len(token):]
                if token[:1] == '"':
                    pdata.append(token[1:-1])
                elif token[:1] == '(':
                    stack.append(pdata)
                    pdata.append([])
                    pdata = pdata[-1]
                elif token[:1] == ')':
                    pdata = stack.pop(-1)
                elif token[:1] not in (' ', '\t', '\n', '\r'):
                    pdata.append(token)
            else:
                break
    return (reply[0].upper() == 'OK'), pdata

# ***************************************************************
# ***************************************************************

CRYPTOBLOBS = "CRYPTOBLOBS"
INDEX = "INDEX"
ENCRYPTED = "ENCRYPTED"

parent = imaplib.IMAP4_SSL

# we need to keep track of imap state
class IMAP4_SSL(imaplib.IMAP4_SSL):
    pass

    def __init__(self, host = '', port = imaplib.IMAP4_SSL_PORT, keyfile = None, certfile = None):
        imaplib.IMAP4_SSL.__init__(self, host, port, keyfile, certfile)
        self.mapping = None
        self.selected_mailbox = "INBOX"

    def find_index_id(self):
        imaplib.IMAP4_SSL.select(self, mailbox=CRYPTOBLOBS)
        typ, data = imaplib.IMAP4_SSL.search(self, None, "SUBJECT", '"'+INDEX+'"')
        return data[0].split()[0]

    def delete_message_from_actual_folder(self, index_id, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=folder)
        typ, data = imaplib.IMAP4_SSL.store(self, str(index_id), "+FLAGS", r'(\Deleted)')
        typ, response = imaplib.IMAP4_SSL.expunge(self)

    def delete_message_from_actual_folder_uid(self, index_id, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=folder)
        typ, data = imaplib.IMAP4_SSL.uid(self, "STORE", str(index_id), "+FLAGS", r'(\Deleted)')
        typ, response = imaplib.IMAP4_SSL.expunge(self)

    def delete_index(self, index_id):
        self.delete_message_from_actual_folder(index_id, CRYPTOBLOBS)

    def load_index(self, index_id):
        imaplib.IMAP4_SSL.select(self, mailbox=CRYPTOBLOBS)
        typ, data = imaplib.IMAP4_SSL.fetch(self, index_id, '(BODY[TEXT])')
        # TODO: decrypt message
        return json.loads(data[0][1].strip())

    def encrypt_and_append_message(self, message):
        new_body = str(message)
        # TODO: encrypt message
        self.append_encrypted_message(new_body)

    def append_encrypted_message(self, message_body):
        message = Message()
        message['Subject'] = ENCRYPTED
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        message.set_payload(message_body)
        typ, data = parent.append(self, CRYPTOBLOBS, None, None, str(message))

    def append_index(self, table):
        message = Message()
        message['Subject'] = INDEX
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        message.set_payload(json.dumps(table)+"\n")
        # TODO: encrypt message
        typ, data = imaplib.IMAP4_SSL.append(self, CRYPTOBLOBS, None, None, str(message))

    # assumes cryptoblobs and index already exist
    def save_index(self, table):
        index_id = self.find_index_id()
        # delete original index
        self.delete_index(index_id)
        # append new index        
        self.append_index(table)


    def create_cryptoblobs_or_load_index(self):
        if self.mapping != None:
            return
        typ, data = imaplib.IMAP4_SSL.list(self)
        names = [line.split()[-1].strip('"') for line in data]
        # create cryptoblobs folder if one does not yet exist
        if not CRYPTOBLOBS in names:
            print "creating cryptoblobs"
            imaplib.IMAP4_SSL.create(self, CRYPTOBLOBS)
            self.append_index({})
        # unload the index
        index_id = self.find_index_id()
        self.mapping = self.load_index(index_id)
        print "loaded index", self.mapping

    def login(self, user, password):
        imaplib.IMAP4_SSL.login(self, user, password)
        self.create_cryptoblobs_or_load_index()

    # ********************************************************** #
    # the following methods are called by mailpile
    # ********************************************************** #

    def list(self, directory='""', pattern='*'):
        self.create_cryptoblobs_or_load_index()
        typ, data = imaplib.IMAP4_SSL.list(self, directory, pattern)
        print "list", data
        return typ, data

    def noop(self):
        self.create_cryptoblobs_or_load_index()
        typ, data = imaplib.IMAP4_SSL.noop(self)
        # print "noop", data
        return typ, data

    # switches which mailbox we're prodding for updates in
    def select(self, mailbox='INBOX', readonly=False):
        self.create_cryptoblobs_or_load_index()
        self.selected_mailbox = mailbox
        typ, data = imaplib.IMAP4_SSL.select(self, mailbox, readonly)
        print "select", mailbox, data
        return typ, data

    # asks for and receives email
    # command=SEARCH returns a list of the uids in the current mailbox
    # command=FETCH fetches a specific message?
    # it can also be SORT and THREAD.
    def uid(self, command, *args):
        self.create_cryptoblobs_or_load_index()
        typ, data = imaplib.IMAP4_SSL.uid(self, command, *args)
        command = command.upper()
        if command == "FETCH" and "BODY" in args[1]:
            print args
            uid = args[0]
            folder = self.selected_mailbox
            if len(args) >= 3:
                folder = args[2]
            # TODO: actually handle case where this is the index that's been
            if folder == CRYPTOBLOBS:
                return # ignore it for now
            # updated by another client

            # assume this is the first time we've fetched it
            # (as in we wouldn't be fetching it unless it's changed on the server)
            # delete it off the server
            self.delete_message_from_actual_folder_uid(uid, folder)

            # update it in the index
            if not folder in self.mapping:
                self.mapping[folder] = []
            self.mapping[folder].append(uid)

            # save the index
            self.save_index(self.mapping)

            # reupload message to the cryptoblobs folder
            self.encrypt_and_append_message(Message(data[0][1].strip()))

        print "uid", command#, _parse_imap(a)
        # _parse_imap will only work when it's not FETCH.
        # from mailbox import Mailbox, Message
        #Message(data)
        #if 


        return typ, data

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


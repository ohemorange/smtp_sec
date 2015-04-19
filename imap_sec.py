import imaplib, time
import re
from mailbox import Message
import json
import sys
import traceback
import threading
import hashlib
import random
import pickle
import scrypt # sudo -H pip install scrypt
from crypticle import Crypticle

import imap_scheduler

class IMAP4(imaplib.IMAP4):
    pass
    # override/add here
    def __init__(self):
        raise NotImplementedError("Do not use this class")

CRYPTOBLOBS = "CRYPTOBLOBS"
INDEX = "INDEX"
INBOX = "INBOX"
ENCRYPTED = "ENCRYPTED"
SEQUENCE_NUMBER = "SEQUENCE_NUMBER"
FAKE_MESSAGES = "FAKE_MESSAGES"
SMTorP = "SMTorP"
NEXT_UID = "NEXT_UID"
LOCK = "LOCK"
GMAIL_ALL_MAIL = "[Gmail]/All Mail"
OK = "OK"

parent = imaplib.IMAP4_SSL

CRLF = imaplib.CRLF

IMAP4_SSL_PORT = imaplib.IMAP4_SSL_PORT

TOTAL_LOCK_RECOVERY_TIME = 60.0 # this may need to be dependent on mix num
LOCK_RETRY_DELAY = 2

MIX_NUMBER = 5

# Some flags that are helpful for debugging
DEBUG_IMAP_FROM_GMAIL = False
DEBUG_IMAP_FROM_SMTORP = False
DEBUG_SCHEDULER = False
DEBUG_EXTRAS = False
DEBUG_METHODS_ARGS_RETURNS = True
PRINT_INDEX = True
DEBUG_LOCK = False
DEBUG_RESPONSES = False
DEBUG_TURN_OFF_INDEX_REFETCH = True
NOOP_ENCRYPTION = False

def hash_of_message_as_string(message_as_string):
    if DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL:
        print "in hash_of_message_as_string"
    hashed = hashlib.md5(message_as_string)
    if DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL:
        print "hashed", hashed
    hexed = hashed.hexdigest()
    if DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL:
        print "hexed", hexed
    return hexed

def get_new_unique_subject():
    return '%032x' % random.randrange(16**32)

def fake_message_with_random_contents_as_string():
    message = Message()
    message['Subject'] = "garbage"
    message['From'] = "foo@bar.com"
    message['To'] = "foo@bar.com"
    message.set_payload(str(random.randint(0,10000000000)))
    return str(message)

def replace_item_in_tuple(d, replacement, x, y):
    if DEBUG_METHODS_ARGS_RETURNS:
        print "replace_item_in_tuple"
    ld = list(d)
    ldd = list(d[x])
    ldd[y] = replacement
    ld[x] = tuple(ldd)
    ldt = tuple(ld)
    if DEBUG_METHODS_ARGS_RETURNS:
        print "replaced item_in_tuple"
    return ldt

def delete_item_from_tuple(d, x, y):
    ld = list(d)
    ldd = list(d[x])
    ldd.pop(y)
    ld[x] = tuple(ldd)
    ldt = tuple(ld)
    return ldt

# we need to keep track of imap state
class IMAP4_SSL(imaplib.IMAP4_SSL):
    pass

    # if local store file isn't specified, we can't guarantee that the
    # index hasn't been rolled back
    # if local send/delete queue file isn't specified and we're shut down before
    # all messages that came in from SMTorP are sent, we can't resend/delete
    # when the next session starts.
    # please specify a passphrase. leaving this to the caller.
    def __init__(self, passphrase, host='',port=imaplib.IMAP4_SSL_PORT,
                 keyfile=None, certfile=None, timer_tick=120,
                 local_store_file=None, local_send_queue_file=None,
                 local_delete_queue_file=None):
        if DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL \
            or DEBUG_IMAP_FROM_SMTORP or DEBUG_EXTRAS:
            print "initializing IMAP4_SSL(imap_sec)", host, port, passphrase
            print "local_store_file", local_store_file
            print "local_send_queue_file", local_send_queue_file
            print "local_delete_queue_file", local_delete_queue_file
        imaplib.IMAP4_SSL.__init__(self, host, port, keyfile, certfile)

        self.mapping = None # this will be loaded in load_cryptoblobs
        self.selected_mailbox = INBOX
        
        # load locally stored index number
        self.local_store_file = local_store_file
        self.load_last_index_number_from_disk()

        self.rollback_detected = False
        self._scheduler = imap_scheduler.ImapScheduler()
        
        self.passphrase = passphrase
        # we can't derive the key until we've pulled down the index
        # to get the salt
        self.random_salt = None
        self.index_subject = None
        self.encryption_key = None

        self.have_index_lock = False

        self.local_send_queue_file = local_send_queue_file
        self.load_send_queue_from_disk()
        self.local_delete_queue_file = local_delete_queue_file
        self.load_delete_queue_from_disk()

        self.timer_tick = timer_tick
        
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "made it through initialization of IMAP4_SSL", self

    # lazily construct this, because we need to have called down
    # the index or created a new one to get the salt
    def key_derived_from_passphrase(self):
        if DEBUG_EXTRAS:
            print "key_derived_from_passphrase", self.passphrase, self.random_salt
        assert self.random_salt
        if not self.encryption_key:
            if DEBUG_EXTRAS:
                print "creating self.encryption_key"
            self.encryption_key = scrypt.hash(self.passphrase, self.random_salt)
        return self.encryption_key


    def uid_for_constructed_message(self, message_as_string, folder):
        if folder == FAKE_MESSAGES:
            a = hash_of_message_as_string(message_as_string)
            s = '11111111111111111111111111111111'
            return str(int(int(a,16)&int(s,2)))
        if folder == SMTorP:
            # self.fetch_and_load_index() # theoretically, we should call
                            # this. but in this implementation, it's extra.
                # actually, it would be bad to call this twice because
                # the double index call would be a signal that this is a
                # real message
            if not NEXT_UID in self.mapping:
                self.mapping[NEXT_UID] = {}
            if not folder in self.mapping[NEXT_UID]:
                self.mapping[NEXT_UID][folder] = 1
            out = self.mapping[NEXT_UID][folder]
            self.mapping[NEXT_UID][folder] += 1
            return str(out)
        # it shouldn't be anything else

    def load_last_index_number_from_disk(self):
        if self.local_store_file:
            try:
                self.last_index_number = pickle.load(open(self.local_store_file, "rb"))
                if DEBUG_EXTRAS:
                    print "loaded index number", self.last_index_number
            except:
                self.last_index_number = 0
        else:
            self.last_index_number = 0

    def load_send_queue_from_disk(self):
        if self.local_send_queue_file:
            try:
                self.send_queue = pickle.load(open(self.local_send_queue_file, "rb"))
            except:
                self.send_queue = []
        else:
            self.send_queue = []

    def load_delete_queue_from_disk(self):
        if self.local_delete_queue_file:
            try:
                self.delete_queue = pickle.load(open(self.local_delete_queue_file, "rb"))
            except:
                self.delete_queue = []
        else:
            self.delete_queue = []

    def save_send_queue_to_disk(self):
        if self.local_send_queue_file != None:
            if DEBUG_SCHEDULER:
                print "trying to save send queue to", self.local_send_queue_file
            pickle.dump(self.send_queue, open(self.local_send_queue_file, "wb"))

    def save_delete_queue_to_disk(self):
        if self.local_delete_queue_file != None:
            if DEBUG_SCHEDULER:
                print "trying to save delete queue to", self.local_delete_queue_file
            pickle.dump(self.delete_queue, open(self.local_delete_queue_file, "wb"))

    def quote(self, item):
        return '"'+item+'"'

    def find_index_uid_in_folder(self, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(folder))
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "find_index_uid_in_folder folder", folder
        typ, data = imaplib.IMAP4_SSL.uid(self, 'SEARCH', None, "SUBJECT", self.quote(INDEX))
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "find_index_uid_in_folder", typ, data
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
        if DEBUG_IMAP_FROM_GMAIL or DEBUG_EXTRAS:
            print "found index id", data
        return data[0].split()[0]

    def get_list_of_uids_given_subject_line(self, subject_line, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(folder))
        typ, data = imaplib.IMAP4_SSL.uid(self, 'SEARCH', None, "SUBJECT", self.quote(subject_line))
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
        return data[0].split()

    def get_message_uid_given_hash_in_subject(self, hash_of_message):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "get_message_uid_given_hash_in_subject", hash_of_message
        return self.get_list_of_uids_given_subject_line(hash_of_message, CRYPTOBLOBS)[0]

    def delete_message_from_actual_folder_uid(self, index_id, folder):
        if DEBUG_EXTRAS:
            print "delete_message_from_actual_folder_uid", index_id, folder
        a, b = imaplib.IMAP4_SSL.select(self, mailbox=self.quote(folder))
        if DEBUG_IMAP_FROM_GMAIL:
            print "selected folder", a, b
        typ, data = imaplib.IMAP4_SSL.uid(self, "STORE", str(index_id), "+FLAGS", r'(\Deleted)')
        if DEBUG_IMAP_FROM_GMAIL:
            print "delete response", typ, data
        typ, response = imaplib.IMAP4_SSL.expunge(self)
        if DEBUG_IMAP_FROM_GMAIL:
            print "expunge response", typ, response
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
        return typ, response

    def delete_index(self):
        index_id = self.find_index_uid_in_folder(CRYPTOBLOBS)
        self.delete_message_from_actual_folder_uid(index_id, CRYPTOBLOBS)
        self.delete_index_from_all_mail()

    # this method checks and sets the rollback_detected flag
    # if rollback is detected, it returns the current index
    def unpack_index_contents(self, decrypted_index_body_text):
        table = json.loads(decrypted_index_body_text)
        if table[SEQUENCE_NUMBER] < self.last_index_number:
            if DEBUG_IMAP_FROM_GMAIL:
                print "rollback_detected"
            self.rollback_detected = True
            return self.mapping
        return table

    def decrypt_string(self, data):
        # decrypt string, check that it decrypted correctly
        if NOOP_ENCRYPTION:
            return data
        else:
            crypt = Crypticle(self.key_derived_from_passphrase())
            if DEBUG_EXTRAS:
                print "crypt created perfectly well", crypt
            out = crypt.loads(data)
            return out
            # returns None if it failed

    def encrypt_string(self, data):
        # encrypt string, add auth
        if NOOP_ENCRYPTION:
            return data
        else:
            crypt = Crypticle(self.key_derived_from_passphrase())
            return crypt.dumps(data)

    def extract_salt_from_subject(self, subject):
        return subject.split()[2]

    def save_salt_and_related_information(self, random_salt):
        if DEBUG_EXTRAS:
            print "save_salt_and_related_information", random_salt
        self.random_salt = random_salt
        self.index_subject = INDEX + " " + self.random_salt
        if DEBUG_EXTRAS:
            print "saved salt and related information."

    def fetch_and_load_index(self, refetch_index=True):
        if DEBUG_EXTRAS or DEBUG_METHODS_ARGS_RETURNS:
            print "fetch_and_load_index"

        if DEBUG_TURN_OFF_INDEX_REFETCH or not refetch_index:
            if self.mapping:
                if PRINT_INDEX:
                    print "Index:"
                    print self.mapping

                return self.mapping


        # 1. fetch index and index subject
        index_id = self.find_index_uid_in_folder(CRYPTOBLOBS)
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(CRYPTOBLOBS))
        # fetches the text of message with id index_id
        typ, data = imaplib.IMAP4_SSL.uid(self, "FETCH", index_id,\
            '(BODY[TEXT])')
        # fetches the subject of message with id index_id
        ok, subject_data = imaplib.IMAP4_SSL.uid(self, "FETCH", index_id,\
            '(BODY[HEADER.FIELDS (SUBJECT)])')
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))

        # 1.5. save salt and related information
        if DEBUG_EXTRAS:
            print "subject_data", subject_data
        subject_line = subject_data[0][1].strip()
        if DEBUG_EXTRAS:
            print "stripped", subject_line
        salt = self.extract_salt_from_subject(subject_line)
        self.save_salt_and_related_information(salt)       

        # 2. decrypt or return None if it fails to decrypt
        unloaded_data = data[0][1].strip()
        decrypted = self.decrypt_string(unloaded_data)
        if not decrypted:
            if DEBUG_EXTRAS:
                print "decryption failed"
            return

        if DEBUG_EXTRAS:
            print "decryption succeeded"

        # 3. unjsonify, check for rollback, and verify
        unpacked_table = self.unpack_index_contents(decrypted)
        if not unpacked_table:
            return

        # 4. replace current index and sequence number in memory
        self.mapping = unpacked_table
        self.last_index_number = unpacked_table[SEQUENCE_NUMBER]

        if PRINT_INDEX:
            print "Index:"
            print self.mapping

        # 5. save new sequence number to disk
        self.save_index_sequence_number_to_disk()

    def encrypt_and_append_message(self, message_contents, unique_subject):
        encrypted_message = self.encrypt_string(message_contents)
        self.append_encrypted_message(encrypted_message, unique_subject)

    def append_encrypted_message(self, encrypted_message_body, hashed):
        message = Message()
        message['Subject'] = ENCRYPTED+" "+hashed
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        message.set_payload(str(encrypted_message_body))
        typ, data = parent.append(self, CRYPTOBLOBS, None, None, str(message))

    def decrypt_and_unpack_message(self, message_contents):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "decrypt_and_unpack_message"
        messageified = Message(message_contents)
        old_message_str = messageified.get_payload()
        a = self.decrypt_string(old_message_str)
        if DEBUG_METHODS_ARGS_RETURNS:
            print "decrypted and_unpacked message"
        return a

    # pushes up the index to the cryptoblobs folder
    # doesn't matter which folder is selected
    def append_index(self, table):
        if DEBUG_EXTRAS:
            print "append_index", self.index_subject
        message = Message()
        message['Subject'] = self.index_subject
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        encrypted_contents = self.encrypt_string(json.dumps(table))
        message.set_payload(encrypted_contents)
        str_message = str(message)
        typ, data = imaplib.IMAP4_SSL.append(self, CRYPTOBLOBS, None, \
            None, str_message)
        if DEBUG_IMAP_FROM_GMAIL or DEBUG_EXTRAS:
            print "append_index", typ, data

    def append_lock(self):
        message = Message()
        message['Subject'] = LOCK
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        str_message = str(message)
        typ, data = imaplib.IMAP4_SSL.append(self, CRYPTOBLOBS, None, \
            None, str_message)

    def save_index_sequence_number_to_disk(self):
        if DEBUG_SCHEDULER:
            print "save_index_sequence_number_to_disk"
        if self.local_store_file != None:
            if DEBUG_SCHEDULER:
                print "trying to save index sequence number to", self.local_store_file
            pickle_file = open(self.local_store_file, "wb")
            if DEBUG_EXTRAS:
                print "opened file", pickle_file
            pickle.dump(self.mapping[SEQUENCE_NUMBER], pickle_file)
        else:
            if DEBUG_SCHEDULER:
                print "no local store file"

    def find_lock_uid_in_folder(self, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(folder))
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "find_lock_uid_in_folder folder", folder
        typ, data = imaplib.IMAP4_SSL.uid(self, 'SEARCH', None, "SUBJECT", self.quote(LOCK))
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "find_lock_uid_in_folder", typ, data
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
        if DEBUG_IMAP_FROM_GMAIL or DEBUG_EXTRAS:
            print "found lock id", data
        if data[0] == '':
            return None
        return data[0].split()[0]

    def acquire_index_lock(self):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "acquire_index_lock"
        if self.have_index_lock:
            if DEBUG_EXTRAS:
                print "already have index lock"
            return
        try_time = 0
        timeout = TOTAL_LOCK_RECOVERY_TIME
        while True:
            if DEBUG_LOCK:
                print "try_time", try_time, "out of", timeout
            if DEBUG_EXTRAS:
                print "trying to acquire index lock"
            # find lock id
            lock_id = self.find_lock_uid_in_folder(CRYPTOBLOBS)
            if lock_id == None:
                if DEBUG_SCHEDULER or DEBUG_LOCK:
                    print 'lock not in there'
                try_time += LOCK_RETRY_DELAY
                # if it's been too long
                if try_time >= timeout:
                    # is the index there?
                    try:
                        prev_sequence_num = self.mapping[SEQUENCE_NUMBER]
                        self.fetch_and_load_index() # TODO: ensure that this excepts
                        # the index is there.
                        if DEBUG_LOCK:
                            print "the index is there"
                        # if the index sequence number hasn't changed
                        if prev_sequence_num == self.mapping[SEQUENCE_NUMBER]:
                            # just get the lock
                            if DEBUG_LOCK:
                                print "index number hasn't changed"
                            # make sure it's not in all mail
                            try:
                                self.delete_lock_from_all_mail()
                            except:
                                pass
                            self.have_index_lock = True
                            return
                        # if it has
                        else:
                            # double timeout (exponential backoff)
                            timeout = 2 * timeout
                    except:
                        # index isn't there. our turn!
                        # make sure index is also gone from all mail
                        try:
                            self.delete_index_from_all_mail()
                        except:
                            pass
                        # make sure it's not in all mail
                        try:
                            self.delete_lock_from_all_mail()
                        except:
                            pass
                        # put up the index
                        self.save_index_without_deleting()
                        # we have the lock now
                        self.have_index_lock = True
                        return
                time.sleep(LOCK_RETRY_DELAY)
                continue
            # try to delete
            # if we fail, we haven't acquired the lock
            typ, data = self.delete_message_from_actual_folder_uid(lock_id, CRYPTOBLOBS)
            if data[0] == None: # otherwise it's ['NUM_MESSAGES_BEFORE_DELETION']
                if DEBUG_SCHEDULER:
                    print "failed to delete"
                try_time = 0 # someone else just touched it, so reset
                time.sleep(LOCK_RETRY_DELAY)
                continue
            # we successfully found the uid and deleted the message
            self.have_index_lock = True
            # so also take it out of all mail
            self.delete_lock_from_all_mail()
            break

    def release_index_lock(self, release_lock):
        if not release_lock:
            return
        if DEBUG_METHODS_ARGS_RETURNS:
            print "release_index_lock"
        if self.have_index_lock:
            # put up a message with subject "LOCK"
            self.have_index_lock = False
            self.append_lock()

    def save_index_without_deleting(self):
        # increment the sequence number
        self.mapping[SEQUENCE_NUMBER] = self.mapping[SEQUENCE_NUMBER] + 1
        # save the new sequence number to disk
        self.save_index_sequence_number_to_disk()
        if DEBUG_SCHEDULER:
            print "successfully saved index seq number to disk or didn't"
        # append new index
        if DEBUG_SCHEDULER:
            print "new index about to be uploaded", self.mapping
        self.append_index(self.mapping)

    # assumes cryptoblobs and index already exist
    # this method only pushes up. we should have already updated from the
    # new one by pulling down.
    def save_index(self):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "saving index"
        if DEBUG_IMAP_FROM_GMAIL:
            print "old index id"
        if DEBUG_SCHEDULER:
            print "old index", self.mapping
        # delete original index
        self.delete_index()
        self.save_index_without_deleting()

    def create_cryptoblobs_or_load_index(self):
        if DEBUG_EXTRAS or DEBUG_METHODS_ARGS_RETURNS:
            print "create_cryptoblobs_or_load_index"
        if self.mapping != None:
            if DEBUG_SCHEDULER:
                print "self.mapping exists"
            return
        typ, data = imaplib.IMAP4_SSL.list(self)
        names = [line.split()[-1].strip('"') for line in data]
        if DEBUG_SCHEDULER:
            print "names", names
        # create cryptoblobs folder if one does not yet exist
        if not CRYPTOBLOBS in names:
            if DEBUG_IMAP_FROM_GMAIL or DEBUG_SCHEDULER or DEBUG_EXTRAS:
                print "creating cryptoblobs"
            imaplib.IMAP4_SSL.create(self, CRYPTOBLOBS)
            random_salt = str(random.randint(0,10000000000))
            self.save_salt_and_related_information(random_salt)
            self.append_index({SEQUENCE_NUMBER: 1})
            self.append_lock()
            # unload the index
            self.fetch_and_load_index()
            # this makes it time out. ah well.
            # for i in range(0, MIX_NUMBER):
            #     print "push up next fake"
            #     self.push_up_next_message(force_fake=True)
        else:
            # just unload the index
            self.fetch_and_load_index()
        if DEBUG_IMAP_FROM_GMAIL or DEBUG_SCHEDULER:
            print "loaded index", self.mapping

    def login(self, user, password):
        if DEBUG_EXTRAS:
            print "login"
        a = imaplib.IMAP4_SSL.login(self, user, password)
        self.create_cryptoblobs_or_load_index()
        return a

    # implicitly called by the constructor
    def open(self, host = '', port = IMAP4_SSL_PORT):
        a = imaplib.IMAP4_SSL.open(self, host, port)
        # print "opening mailbox", host, port()
        return a 

    # ********************************************************** #
    # the following methods are called by mailpile
    # ********************************************************** #

    def list(self, directory='""', pattern='*'):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "list", directory, pattern
        typ, data = imaplib.IMAP4_SSL.list(self, directory, pattern)
        if typ == OK:
            # find the index of the one to delete
            found = False
            for i in range(0, len(data)):
                if CRYPTOBLOBS in data[i]:
                    delete_index = i
                    found = True
                    break
            # delete it
            if found:
                string_format = data.pop(delete_index)

            # if directory is the top
            if directory == '""' or directory == "":
                # append things from the index, if they're not
                # already in there as having no children
                # start = string_format.index(CRYPTOBLOBS)
                # before = string_format[:start]
                # after = string_format[start+len(CRYPTOBLOBS):]
                before = '(\\HasNoChildren) "/" "'
                after = '"'
                self.fetch_and_load_index()
                to_append = []
                for folder in self.mapping.keys():
                    # search through lines in data
                    if folder == SEQUENCE_NUMBER or folder == FAKE_MESSAGES\
                       or folder == NEXT_UID:
                        continue
                    found = False
                    for line in data:
                        if folder in line:
                            found = True
                            break
                    if not found:
                        to_append.append(folder)
                for folder_name in to_append:
                    string = before + folder_name + after
                    data.append(string)

        if DEBUG_IMAP_FROM_GMAIL or DEBUG_METHODS_ARGS_RETURNS:
            print "list data", typ, data
        return typ, data

    def noop(self):
        if DEBUG_SCHEDULER:
            print "noop", self
        typ, data = imaplib.IMAP4_SSL.noop(self)
        # print "noop", data
        return typ, data

    # switches which mailbox we're prodding for updates in
    def select(self, mailbox='INBOX', readonly=False):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "select", mailbox
        # don't let it ask for cryptoblobs
        mb = mailbox
        folder = mb.strip('"')
        if folder in [GMAIL_ALL_MAIL, CRYPTOBLOBS, FAKE_MESSAGES, SEQUENCE_NUMBER, NEXT_UID]:
            self.selected_mailbox = folder
            return OK, ['0']
        # add the number from the index
        typ, data = imaplib.IMAP4_SSL.select(self, mb, readonly)
        if typ == OK or (typ == "NO" and folder in self.mapping):
            self.selected_mailbox = folder
            self.fetch_and_load_index()
            if typ == "NO":
                data = ['0']
                typ = OK
            if folder in self.mapping:
                count = len(self.mapping[folder])
                the_sum = count + int(data[0])
                data[0] = str(the_sum)
        if DEBUG_METHODS_ARGS_RETURNS:
            print "select data", mailbox, typ, data
        return typ, data

        nonsense = "ASDFKASFKACXMCMCKWDMFOEWEKR"
        if mb.strip('"') == CRYPTOBLOBS:
            mb = nonsense
        typ, data = imaplib.IMAP4_SSL.select(self, mb, readonly)
        if typ == OK:
            self.selected_mailbox = mailbox.strip('"')
        if mb == nonsense:
            # replace CRYPTOBLOBS
            string_format = data[0]
            if nonsense in string_format:
                start = string_format.index(nonsense)
                before = string_format[:start]
                after = string_format[start+len(nonsense):]
                new_string = before + CRYPTOBLOBS + after
                data[0] = new_string
        if DEBUG_IMAP_FROM_GMAIL:
            print "select", mailbox, mb, data
        return typ, data
    
    def timed_imap_exchange(self):
        if DEBUG_SCHEDULER or DEBUG_METHODS_ARGS_RETURNS:
            print "imap timer tick"

        if self._scheduler.next_time_point_action_is_push():
            # push up message
            if DEBUG_SCHEDULER or DEBUG_METHODS_ARGS_RETURNS:
                print "up"
            self.push_up_next_message()
        else:
            # pull down (delete) message from imap
            if DEBUG_SCHEDULER or DEBUG_METHODS_ARGS_RETURNS:
                print "down"
            self.pull_down_next_message()

    def push_up_next_message(self, force_fake=False):
        message_contents = ""
        folder = ""
        uid = ""
        generate = False
        if len(self.send_queue) >= 1 and not force_fake:
            if DEBUG_IMAP_FROM_SMTORP or DEBUG_SCHEDULER:
                print "pushing up next message"
            (message_contents, folder, uid, generate_uid) = self.send_queue[0]
            generate = generate_uid
            self.send_queue = self.send_queue[1:]
            self.save_send_queue_to_disk()
        else:
            # push up a fake message
            if DEBUG_SCHEDULER:
                print "push up a fake message"
            # construct fake message
            folder = FAKE_MESSAGES
            # just put into a FAKE_MESSAGES pseudo-folder in cryptoblobs!
            message_contents = fake_message_with_random_contents_as_string()
            if DEBUG_SCHEDULER:
                print "fake message:\n", message_contents
            uid = ""
            generate = True
            # append onto index's list of fake messages
            if DEBUG_SCHEDULER:
                print "uid", uid

        if DEBUG_SCHEDULER:
            print "folder, uid", folder, uid

        self.add_message_to_folder_internal(message_contents,
                folder, uid, False, generate_uid=generate, mix=(not force_fake))
        self._scheduler.message_was_pushed()

    def pull_down_next_message(self):
        # check messages to delete and pull down one of those.
        # otherwise, pull down a fake message. also save delete queue to
        # disk.
        if len(self.delete_queue) >= 1:
            raise NotImplementedError("No code should call this")
        else:
            # pull down a fake message
            # choose which fake message to pull down
            self.acquire_index_lock()
            self.fetch_and_load_index()
            # this will sync the index to make sure we know about all
            # fake messages
            if FAKE_MESSAGES not in self.mapping \
                or len(self.mapping[FAKE_MESSAGES]) == 0:
                if DEBUG_SCHEDULER:
                    print "no fake messages to pull down"
                return
            delete_uid = random.choice(self.mapping[FAKE_MESSAGES].keys())
        if DEBUG_SCHEDULER:
            print "pulling down fake message", delete_uid
        hash_of_message = self.mapping[FAKE_MESSAGES][delete_uid]
        self.delete_message_from_pseudo_folder(delete_uid, FAKE_MESSAGES)
        self._scheduler.message_was_pulled()

    # message_contents is the message as a string. get by calling str(message)
    # where message is a Message object.
    def add_message_to_folder(self, message_contents, folder):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "add_message_to_folder", folder
        # we've called this from an external class, so it can't be the index.
        self.add_message_to_folder_internal(message_contents, folder,
            "", True, generate_uid=True)
        if DEBUG_METHODS_ARGS_RETURNS:
            print "added message to folder", folder

    def choose_k_messages_to_fetch_then_delete(self, k, extra=None):
        # combine uids from real folders
        combined = []
        for folder in self.mapping:
            if folder in [NEXT_UID, SEQUENCE_NUMBER]:
                continue
            uids = self.mapping[folder].keys()
            combined.extend([(folder, x) for x in uids])
        # choose one more than you should
        num = min(k+1, len(combined))
        sample = random.sample(combined, num)
        # if extra is not none and in there, delete extra
        if extra and extra in sample:
            sample.remove(extra)
        # else, delete the last one
        else:
            sample = sample[:-1]
        return sample

    # <schedule_upload> should be True for messages coming from a
    # metadata-secure source. it should probably be False if we've
    # just pulled the message down from IMAP and are reuploading it.
    # TODO: check to make sure this actually works, and only delete from
    # cache after. because it doesn't, there's no fault tolerance
    # going on...
    # <folder> is a pseudo-folder.
    def add_message_to_folder_internal(self, message_contents, folder,
        uid, schedule_upload, generate_uid=False, mix=True, \
        release_lock=True, refetch_index=True):
        uid = str(uid)
        if DEBUG_IMAP_FROM_SMTORP or DEBUG_SCHEDULER:
            print "add_message_to_folder", self, "schedule for later", schedule_upload
        if schedule_upload:
            # place it on the queue, deal with it later
            # if messages aren't sent, they'll be pickled and sent next time
            self.send_queue.append((message_contents, folder, uid, generate_uid))
            self.save_send_queue_to_disk()
            return
        # update it in the index
        if DEBUG_IMAP_FROM_SMTORP or DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL:
            # print "message_contents", message_contents
            print "folder", folder
            print "uid", uid
            print "host", self.host
            print "port", self.port

        # these calls are atomic
        self.acquire_index_lock()
        self.fetch_and_load_index(refetch_index=refetch_index)

        selected_cache = self.selected_mailbox

        if not folder in self.mapping:
            self.mapping[folder] = {}

        if generate_uid:
            uid = self.uid_for_constructed_message(message_contents, folder)

        saved_messages_and_data = [(uid, folder, message_contents)]

        if mix:
            self.choose_fetch_delete_and_save_k_messages(MIX_NUMBER, saved_messages_and_data)

        # now we have k+1 tuples in saved_messages_and_data, none of which
        # are in the index or in actual folder
        for uid, folder, message_contents in saved_messages_and_data:
            unique_subject = get_new_unique_subject()
            self.mapping[folder][uid] = unique_subject

            # reupload message to the cryptoblobs folder
            self.encrypt_and_append_message(message_contents, unique_subject)

        self.selected_mailbox = selected_cache
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))

        # save the index
        if DEBUG_IMAP_FROM_GMAIL:
            print "about to try saving index"
        self.save_index()

        self.release_index_lock(release_lock)

    def choose_fetch_delete_and_save_k_messages(self, k, saved_messages_and_data, \
        extra=None):
        # choose k messages to fetch then delete
        chosen_folder_uid_pairs = self.choose_k_messages_to_fetch_then_delete(k, extra=extra)

        if extra:
            # insert it into chosen_folder_uid_pairs
            position = random.randint(0, len(chosen_folder_uid_pairs))
            chosen_folder_uid_pairs.insert(position, extra)

        # fetch and delete each of those messages
        for folder, uid in chosen_folder_uid_pairs:
            self.select(folder)
            message_contents = self.uid("FETCH",uid,"(BODY[TEXT])")[1][0][1].strip()
            if (folder, uid) != extra:
                saved_messages_and_data.append((uid, folder, message_contents))
            self.delete_message_from_pseudo_folder(uid, folder, mix=False, release_lock=False)

    def delete_message_from_pseudo_folder(self, delete_uid, folder, \
            mix=True, release_lock=True, refetch_index=True):
        delete_uid = str(delete_uid)
        if DEBUG_EXTRAS:
            print "delete_message_from_pseudo_folder", delete_uid, folder
        # these calls are atomic
        self.acquire_index_lock()
        self.fetch_and_load_index(refetch_index=refetch_index) # this should be redundant

        if DEBUG_SCHEDULER:
            print "delete folder in self.mapping", folder in self.mapping
            print "uid in there where we want it", delete_uid in self.mapping[folder]

        selected_cache = self.selected_mailbox

        saved_messages_and_data = []

        if mix:
            self.choose_fetch_delete_and_save_k_messages(MIX_NUMBER, \
                saved_messages_and_data, extra=(folder,delete_uid))

        # now we have k tuples in saved_messages_and_data, none of which
        # are in the index or in actual folder
        for uid, folder, message_contents in saved_messages_and_data:
            unique_subject = get_new_unique_subject()
            self.mapping[folder][uid] = unique_subject

            # reupload message to the cryptoblobs folder
            self.encrypt_and_append_message(message_contents, unique_subject)

        if not mix:
            # delete_uid is the old uid that's not meaningful to us
            # we want the hash of the message, because it'll be in the
            # subject string, and we can use that to find the actual
            # uid to delete.
            hash_of_message = self.mapping[folder][delete_uid]

            actual_uid = self.get_message_uid_given_hash_in_subject(hash_of_message)

            del self.mapping[folder][delete_uid]

            # reupload message to the cryptoblobs folder
            self.delete_message_from_actual_folder_uid(actual_uid, CRYPTOBLOBS)
            self.delete_from_all_mail_by_subject(hash_of_message)

        # clean up
        self.selected_mailbox = selected_cache
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))

        # save the index
        self.save_index()

        self.release_index_lock(release_lock)

    # assumes only one of that subject in that folder exists
    def delete_from_all_mail_by_subject(self, subject_substring):
        uid = self.get_list_of_uids_given_subject_line(subject_substring, \
                                                       GMAIL_ALL_MAIL)[0]
        self.delete_message_from_actual_folder_uid(uid, GMAIL_ALL_MAIL)

    def delete_index_from_all_mail(self):
        self.delete_from_all_mail_by_subject(INDEX)

    def delete_lock_from_all_mail(self):
        self.delete_from_all_mail_by_subject(LOCK)

    def delete_message_from_all_other_folders_given_subject(self, subject):
        folder = GMAIL_ALL_MAIL

        uids = self.get_list_of_uids_given_subject_line(subject, folder)

        new_uid = uids[0]

        # delete that uid from all mail
        self.delete_message_from_actual_folder_uid(new_uid, folder)

    def delete_message_from_all_other_folders(self, message_contents):
        # TODO this only works for this exact setup, with gmail. if
        # you want to use it for something else, have fun! if you're
        # doing gmail, delete from all mail last.
        folder = GMAIL_ALL_MAIL

        # find the uid of the message in gmail by searching for its subject
        messageified = Message(message_contents)
        subject = messageified['Subject'].strip().strip('"')

        uids = self.get_list_of_uids_given_subject_line(subject, folder)

        new_uid = None

        # look through the results to find which one is the right one
        for potential_uid in uids:
            # fetch that message
            imaplib.IMAP4_SSL.select(self, mailbox=self.quote(folder))
            typ, data = imaplib.IMAP4_SSL.uid(self, 'FETCH', potential_uid, '(BODY[])')
            imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
            new_contents = data[0][1].strip()
            if new_contents == message_contents:
                # use that uid
                new_uid = potential_uid
                break

        if not new_uid:
            return

        # delete that uid from all mail
        self.delete_message_from_actual_folder_uid(new_uid, folder)
        
    def process_new_inbox_message(self, uid):
        uid = str(uid)
        if DEBUG_METHODS_ARGS_RETURNS:
            print "process_new_inbox_message", uid
        # execute acquire for entire message
        typ, data = imaplib.IMAP4_SSL.uid(self, "FETCH", uid, '(BODY[])')
        message_contents = data[0][1].strip()
        
        # cache locally
        # TODO

        # encrypt and upload to CB
        self.add_message_to_folder_internal(message_contents, INBOX, uid, False, mix=False)
        
        # delete from inbox
        self.delete_message_from_actual_folder_uid(uid, INBOX)
        
        # delete from everywhere else
        self.delete_message_from_all_other_folders(message_contents)
        
        
        

    # asks for and receives email
    # command=SEARCH returns a list of the uids in the current mailbox
    # command=FETCH fetches a specific message?
    # it can also be SORT and THREAD.
    # do not call with the folder as an argument
    def uid(self, orig_command, *args):
        if DEBUG_METHODS_ARGS_RETURNS:
            print "uid", orig_command, args

        folder = self.selected_mailbox
        original_uid = str(args[0])
        command = orig_command.upper()

        # if this is a search
        if command == "SEARCH":
            # if it's all mail
            if folder == GMAIL_ALL_MAIL:
                # the answer is no. nothing is here.
                typ, data = OK, ['']
            # else (if it's anything else)
            else:
                # fetch the index
                self.fetch_and_load_index()
                # return the result based on the index
                # if the folder's not in self.mapping, just return empty
                if not folder in self.mapping:
                    typ, data = OK, ['']
                else:
                    uid_strings = self.mapping[folder].keys()
                    uid_nums = [int(x) for x in uid_strings]
                    uid_nums.sort()
                    uid_sorted_strings = [str(x) for x in uid_nums]
                    uids = " ".join(uid_sorted_strings)
                    typ, data = OK, [uids]

                # if it's inbox
                if folder == INBOX:
                    # pass the command through
                    typ_in, data_in = imaplib.IMAP4_SSL.uid(self, command, *args)
                    if typ_in != OK:
                        return typ_in, data_in
                    # append to index results
                    typ = typ_in
                    data = [" ".join([data[0], data_in[0]]).strip()]

        # elif this is a fetch
        elif command == "FETCH":
            # get the index
            self.fetch_and_load_index()
            # if this is from the inbox
            if folder == INBOX:
                # check if it's already been processed
                if not (INBOX in self.mapping and original_uid in self.mapping[INBOX]):
                    # process it entirely
                    self.process_new_inbox_message(original_uid)
            # now it's not a new message from the inbox
            # look up hash
            hash_of_message = self.mapping[folder][original_uid]
            # search for hash
            proper_uid = self.get_message_uid_given_hash_in_subject(hash_of_message)
            # use uid of that message
            # execute command with that uid
            args_copy = list(args)
            args_copy[0] = proper_uid
            args_copy_tuple = tuple(args_copy)
            imaplib.IMAP4_SSL.select(self, mailbox=self.quote(CRYPTOBLOBS))
            t, d = imaplib.IMAP4_SSL.uid(self, command, *args_copy_tuple)
            imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
            # decrypt the message we've received and remessageify it
            if t != OK or type(d[0]) == type("hi"):
                if DEBUG_METHODS_ARGS_RETURNS:
                    print "uid results", t, d
                return t, d
            message_contents = d[0][1].strip()
            message_as_string = self.decrypt_and_unpack_message(message_contents)

            # replace into the form the caller expects it
            ldt = replace_item_in_tuple(d, message_as_string, 0, 1)

            typ = t
            data = ldt

        # just pass it through
        else:
            typ, data = imaplib.IMAP4_SSL.uid(self, command, *args)

        if DEBUG_METHODS_ARGS_RETURNS:
            print "uid results", orig_command, args, typ
        return typ, data

    # ******************************************************** #
    # these methods are like maybe called but less important? 


    def store(self, message_set, command, flags):
        a = imaplib.IMAP4_SSL.store(self, message_set, command, flags)
        print "store", a
        return a   

    def fetch(self, message_set, message_parts):
        a = imaplib.IMAP4_SSL.fetch(self, message_set, message_parts)
        print "fetch", data
        return a

    def capability(self):
        typ, data = imaplib.IMAP4_SSL.capability(self)
        # print "capability", data
        return typ, data

    def search(self, charset, *criteria):
        a = imaplib.IMAP4_SSL.search(self, charset, *criteria)
        return a

    # places all metadata into message
    # replaces with fake metadata
    # calls super to append to cryptoblobs mailbox
    # updates index
    # this will probably not be called.
    def append(self, mailbox, flags, date_time, message):
        typ, data = imaplib.IMAP4_SSL.append(self, mailbox, \
            flags, date_time, message)
        return typ, data

    # ********************************************************* #

    def response(self, code):
        if DEBUG_RESPONSES:
            print "response"
            print "code", code
            print "selected mailbox", self.selected_mailbox
        folder = self.selected_mailbox
        typ, data = imaplib.IMAP4_SSL.response(self, code)

        self.fetch_and_load_index()
        # this is a pseudo-only folder
        if data[0] == None and folder in self.mapping:
            if code == "FLAGS":
                data = ['(\\Answered \\Flagged \\Draft \\Deleted \\Seen $Phishing $NotPhishing)']
            elif code == "RECENT":
                data = ['0'] # I don't think this is used.
            elif code == "UIDVALIDITY":
                data = ['317']
            elif code == "EXISTS":
                # this is a count
                count = len(self.mapping[folder])
                data[0] = str(count)
        # for a hybrid folder, add the two counts
        elif data[0] != None and folder in self.mapping:
            if code == "EXISTS":
                count = len(self.mapping[folder])
                the_sum = count + int(data[0])
                data[0] = str(the_sum)

        if folder == GMAIL_ALL_MAIL and code == "EXISTS":
            data[0] = '0'

        if DEBUG_RESPONSES:
            print "typ", typ
            print "data", data

        return typ, data

    def _get_tagged_response(self, tag):
        a = imaplib.IMAP4_SSL._get_tagged_response(self, tag)
        # print "tag resp", a
        return a

    def readline(self):
        a = imaplib.IMAP4_SSL.readline(self)
        # print "readline:", a
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


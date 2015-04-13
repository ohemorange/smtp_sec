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
ENCRYPTED = "ENCRYPTED"
SEQUENCE_NUMBER = "SEQUENCE_NUMBER"
FAKE_MESSAGES = "FAKE_MESSAGES"
LOCK = "LOCK"
GMAIL_ALL_MAIL = "[Gmail]/All Mail"

parent = imaplib.IMAP4_SSL

CRLF = imaplib.CRLF

IMAP4_SSL_PORT = imaplib.IMAP4_SSL_PORT

LOCK_RETRY_DELAY = 2

DEBUG_IMAP_FROM_GMAIL = False
DEBUG_IMAP_FROM_SMTORP = False
DEBUG_SCHEDULER = False
DEBUG_EXTRAS = False
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

def uid_for_constructed_message(message_as_string):
    return hash_of_message_as_string(message_as_string)

def fake_message_with_random_contents_as_string():
    message = Message()
    message['Subject'] = "garbage"
    message['From'] = "foo@bar.com"
    message['To'] = "foo@bar.com"
    message.set_payload(str(random.randint(0,10000000000)))
    return str(message)

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
        self.selected_mailbox = "INBOX"
        
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
        if DEBUG_EXTRAS:
            print "self.encryption_key", self.encryption_key
        return self.encryption_key

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

    def get_message_uid_given_hash_in_subject(self, hash_of_message):
        folder = "CRYPTOBLOBS"
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(folder))
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "get_message_uid_given_hash_in_subject folder", folder
        typ, data = imaplib.IMAP4_SSL.uid(self, 'SEARCH', None, "SUBJECT", self.quote(hash_of_message))
        if DEBUG_SCHEDULER or DEBUG_EXTRAS:
            print "get_message_uid_given_hash_in_subject", typ, data
        imaplib.IMAP4_SSL.select(self, mailbox=self.quote(self.selected_mailbox))
        if DEBUG_IMAP_FROM_GMAIL or DEBUG_EXTRAS:
            print "found message id", data
        return data[0].split()[0]

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
        # so you can't actually delete from all mail. to handle this in gmail,
        # what we SHOULD be doing is moving to trash then deleting from
        # trash. but then it's gmail specific. not like everything else isn't
        # already.
        # index_id_in_all = self.find_index_uid_in_folder(GMAIL_ALL_MAIL)
        # self.delete_message_from_actual_folder_uid(index_id, GMAIL_ALL_MAIL)

    # this method checks and sets the rollback_detected flag
    # if rollback is detected, it returns the current index
    def unpack_index_contents(self, decrypted_index_body_text):
        if DEBUG_EXTRAS:
            print "unpack_index_contents", decrypted_index_body_text
        table = json.loads(decrypted_index_body_text)
        if DEBUG_IMAP_FROM_GMAIL:
            print "unpacked index", table
        if table[SEQUENCE_NUMBER] < self.last_index_number:
            if DEBUG_IMAP_FROM_GMAIL:
                print "rollback_detected"
            self.rollback_detected = True
            return self.mapping
        if DEBUG_EXTRAS:
            print "returning unpacked index", table
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
            if DEBUG_EXTRAS:
                print "out", out
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

    def fetch_and_load_index(self):
        if DEBUG_EXTRAS:
            print "fetch_and_load_index"

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

        # 5. save new sequence number to disk
        self.save_index_sequence_number_to_disk()

    def encrypt_and_append_message(self, message_contents):
        # turn it into a Message object
        message = Message(message_contents)
        hashed = hash_of_message_as_string(message_contents)
        message['ORIGINAL-FOLDER'] = self.selected_mailbox
        new_body = str(message)
        self.append_encrypted_message(self.encrypt_string(new_body), hashed)

    def append_encrypted_message(self, encrypted_message_body, hashed):
        message = Message()
        message['Subject'] = ENCRYPTED+" "+hashed
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        message.set_payload(str(encrypted_message_body))
        typ, data = parent.append(self, CRYPTOBLOBS, None, None, str(message))

    def decrypt_and_unpack_message(self, message):
        old_message_str = message.get_payload()
        return self.decrypt_string(old_message_str)

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
        if DEBUG_EXTRAS:
            print "str_message", str_message
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
        if self.have_index_lock:
            if DEBUG_EXTRAS:
                print "already have index lock"
            return
        while True:
            if DEBUG_EXTRAS:
                print "trying to acquire index lock"
            # find lock id
            lock_id = self.find_lock_uid_in_folder(CRYPTOBLOBS)
            if lock_id == None:
                time.sleep(LOCK_RETRY_DELAY)
                continue
            # try to delete
            # if we fail, we haven't acquired the lock
            typ, data = self.delete_message_from_actual_folder_uid(lock_id, CRYPTOBLOBS)
            if data[0] == None: # otherwise it's ['NUM_MESSAGES_BEFORE_DELETION']
                time.sleep(LOCK_RETRY_DELAY)
                continue
            # we successfully found the uid and deleted the message
            self.have_index_lock = True
            break

    def release_index_lock(self):
        if self.have_index_lock:
            # put up a message with subject "LOCK"
            self.have_index_lock = False
            self.append_lock()

    # assumes cryptoblobs and index already exist
    # this method only pushes up. we should have already updated from the
    # new one by pulling down.
    def save_index(self):
        if DEBUG_IMAP_FROM_GMAIL:
            print "old index id"
        if DEBUG_SCHEDULER:
            print "old index", self.mapping
        # delete original index
        self.delete_index()
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

    def create_cryptoblobs_or_load_index(self):
        if DEBUG_EXTRAS:
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
        typ, data = imaplib.IMAP4_SSL.list(self, directory, pattern)
        if DEBUG_IMAP_FROM_GMAIL:
            print "list", data
        return typ, data

    def noop(self):
        if DEBUG_SCHEDULER:
            print "noop", self
        typ, data = imaplib.IMAP4_SSL.noop(self)
        # print "noop", data
        return typ, data

    # switches which mailbox we're prodding for updates in
    def select(self, mailbox='INBOX', readonly=False):
        self.selected_mailbox = mailbox.strip('"')
        typ, data = imaplib.IMAP4_SSL.select(self, mailbox, readonly)
        # if DEBUG_IMAP_FROM_GMAIL:
        #     print "select", mailbox, data
        return typ, data
    
    def timed_imap_exchange(self):
        if DEBUG_SCHEDULER:
            print "imap timer tick"

        if self._scheduler.next_time_point_action_is_push():
            # push up message
            if DEBUG_SCHEDULER:
                print "up"
            self.push_up_next_message()
        else:
            # pull down (delete) message from imap
            if DEBUG_SCHEDULER:
                print "down"
            self.pull_down_next_message()

    def push_up_next_message(self):
        message_contents = ""
        folder = ""
        uid = ""
        if len(self.send_queue) >= 1:
            if DEBUG_IMAP_FROM_SMTORP or DEBUG_SCHEDULER:
                print "pushing up next message"
            (message_contents, folder, uid) = self.send_queue[0]
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
            uid = uid_for_constructed_message(message_contents)
            # append onto index's list of fake messages
            if DEBUG_SCHEDULER:
                print "uid", uid

        if DEBUG_SCHEDULER:
            print "folder, uid", folder, uid

        self.add_message_to_folder_internal(message_contents,
                folder, uid, False)
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
        self.delete_message_from_pseudo_folder(delete_uid, FAKE_MESSAGES)
        self._scheduler.message_was_pulled()

    # message_contents is the message as a string. get by calling str(message)
    # where message is a Message object.
    def add_message_to_folder(self, message_contents, folder, uid):
        # we've called this from an external class, so it can't be the index.
        self.add_message_to_folder_internal(message_contents, folder,
            uid, True)

    # schedule_upload should be True for messages coming from a
    # metadata-secure source. it should probably be False if we've
    # just pulled the message down from IMAP and are reuploading it.
    # TODO: check to make sure this actually works. because if it
    # doesn't, there's no fault tolerance going on...
    # folder is a pseudo-folder.
    def add_message_to_folder_internal(self, message_contents, folder,
        uid, schedule_upload):
        if DEBUG_IMAP_FROM_SMTORP or DEBUG_SCHEDULER:
            print "add_message_to_folder", self, "schedule for later", schedule_upload
        if schedule_upload:
            # place it on the queue, deal with it later
            # if messages aren't sent, they'll be pickled and sent next time
            self.send_queue.append((message_contents, folder, uid))
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
        self.fetch_and_load_index()

        if DEBUG_IMAP_FROM_GMAIL:
            print "self.mapping", self.mapping
            # print "self.mapping[folder]", self.mapping[folder]
            # print "self.mapping[folder][uid]", self.mapping[folder][uid]

        if DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL:
            print "folder in self.mapping", folder in self.mapping

        if not folder in self.mapping:
            if DEBUG_IMAP_FROM_GMAIL:
                print "folder isn't in self.mapping"
            self.mapping[folder] = {}

        self.mapping[folder][uid] = hash_of_message_as_string(message_contents)

        if DEBUG_IMAP_FROM_GMAIL:
            print "about to try saving index"

        # save the index
        self.save_index()

        # reupload message to the cryptoblobs folder
        self.encrypt_and_append_message(message_contents)
        self.release_index_lock()

    def delete_message_from_pseudo_folder(self, delete_uid, folder):
        if DEBUG_EXTRAS:
            print "delete_message_from_pseudo_folder", delete_uid, folder
        # these calls are atomic
        self.acquire_index_lock()
        self.fetch_and_load_index() # this should be redundant

        if DEBUG_SCHEDULER:
            print "delete folder in self.mapping", folder in self.mapping
            print "uid in there where we want it", delete_uid in self.mapping[folder]

        # delete_uid is the old uid that's not meaningful to us
        # we want the hash of the message, because it'll be in the
        # subject string, and we can use that to find the actual
        # uid to delete.
        hash_of_message = self.mapping[folder][delete_uid]

        actual_uid = self.get_message_uid_given_hash_in_subject(hash_of_message)

        del self.mapping[folder][delete_uid]

        if DEBUG_SCHEDULER:
            print "removed from mapping", self.mapping

        # save the index
        self.save_index()

        # reupload message to the cryptoblobs folder
        self.delete_message_from_actual_folder_uid(actual_uid, CRYPTOBLOBS)
        self.release_index_lock()

    # asks for and receives email
    # command=SEARCH returns a list of the uids in the current mailbox
    # command=FETCH fetches a specific message?
    # it can also be SORT and THREAD.
    def uid(self, command, *args):
        typ, data = imaplib.IMAP4_SSL.uid(self, command, *args)
        if DEBUG_EXTRAS:
            print "got data from uid", data
        if data == [None]:
            if DEBUG_IMAP_FROM_GMAIL:
                print "args", args
        command = command.upper()
        if command == "FETCH" and "BODY" in args[1]:
            if DEBUG_IMAP_FROM_GMAIL:
                print "args", args
            uid = args[0]
            folder = self.selected_mailbox
            if len(args) >= 3:
                folder = args[2]
            if DEBUG_IMAP_FROM_GMAIL:
                print "in folder", folder
            message_contents = data[0][1].strip()
            messageified = Message(message_contents)
            subject = messageified['Subject'].strip().strip('"')
            if DEBUG_IMAP_FROM_GMAIL:
                print "subject", subject
            if folder == CRYPTOBLOBS or ENCRYPTED in subject or INDEX in subject or LOCK in subject:
                if DEBUG_IMAP_FROM_GMAIL:
                    print "probably not a real message"
                # this could be the index, which means that
                # another client has updated the index
                if (INDEX in subject or LOCK in subject) and folder == CRYPTOBLOBS:
                    # ignore index updates. we only update the index
                    # on our own request. inoming updates are for
                    # messages only.
                    return False, []
                    # TODO: return it as a fake message so we set flags correctly
                    if ok:
                        messageified.set_payload("Everything is awesome.")
                    else:
                        messageified.set_payload("Everything is not awesome.")
                    data[0][1] = str(messageified)
                    # it's probably fine to just have this ui component here,
                    # because it means the server has updated it, and wants us
                    # to grab the rolled back one.
                elif ENCRYPTED in subject and folder == CRYPTOBLOBS:
                    # returns a string
                    # TODO we need to know if we're the ones who just put this there.
                    # if so, ignore for now, maybe change this later.
                    # this definitely has to change. this means another client
                    # put it up here. we should then grab the current index,
                    # check that it's all kosher, and if so then save it down here.
                    return False, []
                    unpacked_message = self.decrypt_and_unpack_message(messageified)
                    data[0][1] = unpacked_message
                    # TODO: do we need to know which folder it belonged in originally?
                    # maybe select the folder
                else:
                    # we're in all mail and the subject is encrypted or cryptoblobs
                    # should probably actually uniquely identify here
                    # TODO
                    return False, []
            else:
                # assume this is the first time we've fetched it
                # (as in we wouldn't be fetching it unless it's changed on the server)
                # delete it off the server
                if DEBUG_EXTRAS:
                    print "actual message", subject

                self.delete_message_from_actual_folder_uid(uid, folder)

                self.add_message_to_folder_internal(message_contents, folder, uid, False)

                # just return the original message to the local client,
                # I'm sure nothing could ever go wrong with thaaaat
        elif command == "SEARCH":
            if DEBUG_IMAP_FROM_GMAIL:
                print "search", data
        if DEBUG_IMAP_FROM_GMAIL:
            print "uid", command#, _parse_imap(a)
        # _parse_imap will only work when it's not FETCH.
        # from mailbox import Mailbox, Message
        #Message(data)
        #if 
        # print "returning data", data
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


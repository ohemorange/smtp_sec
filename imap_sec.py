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
GMAIL_ALL_MAIL = "[Gmail]/All Mail"

parent = imaplib.IMAP4_SSL

CRLF = imaplib.CRLF

IMAP4_SSL_PORT = imaplib.IMAP4_SSL_PORT

DEBUG_IMAP_FROM_GMAIL = False
DEBUG_IMAP_FROM_SMTORP = False
DEBUG_SCHEDULER = False

# TODO: read these from a config, or set based on algorithm.
INITIAL_DT = 30.0
DT = 60.0

def uid_for_constructed_message(message_as_string):
    return hashlib.md5(message_as_string).hexdigest()

def fake_message_with_random_contents_as_string():
    message = Message()
    message['Subject'] = "garbage"
    message['From'] = "foo@bar.com"
    message['To'] = "foo@bar.com"
    message.set_payload("trash")
    return str(message)

# we need to keep track of imap state
class IMAP4_SSL(imaplib.IMAP4_SSL):
    pass

    # if local store file isn't specified, we can't guarantee that the
    # index hasn't been rolled back
    # if local send/delete queue file isn't specified and we're shut down before
    # all messages that came in from SMTorP are sent, we can't resend/delete
    # when the next session starts.
    def __init__(self, host='',port=imaplib.IMAP4_SSL_PORT,
                 keyfile=None, certfile=None, timer_tick=120,
                 local_store_file=None, local_send_queue_file=None,
                 local_delete_queue_file=None):
        if DEBUG_SCHEDULER or DEBUG_IMAP_FROM_GMAIL or DEBUG_IMAP_FROM_SMTORP:
            print "initializing IMAP4_SSL(imap_sec)", host, port
        imaplib.IMAP4_SSL.__init__(self, host, port, keyfile, certfile)
        self.mapping = None
        self.selected_mailbox = "INBOX"
        # load locally stored index number
        if local_store_file:
            self.local_store_file = local_store_file
            self.last_index_number = pickle.load(open(local_store_file, "rb"))
        else:
            self.last_index_number = 0
        self.rollback_detected = False
        self._scheduler = imap_scheduler.ImapScheduler()
        self.send_queue = []
        self.delete_queue = []
        if local_send_queue_file:
            # load send queue from file
            self.local_send_queue_file = local_send_queue_file
            self.load_send_queue_from_disk()
        if local_delete_queue_file:
            self.local_delete_queue_file = local_delete_queue_file
            self.load_delete_queue_from_disk()
        self.timer_tick = timer_tick
        # start a worker that sends every DT. make the first
        # call after time INITIAL_DT
        # threading.Timer(INITIAL_DT, self.timed_imap_exchange).start()
        if DEBUG_SCHEDULER:
            print "initting IMAP4_SSL", self

    def load_send_queue_from_disk():
        self.send_queue = pickle.load(open(self.local_send_queue_file, "rb"))

    def load_delete_queue_from_disk():
        self.delete_queue = pickle.load(open(self.local_delete_queue_file, "rb"))

    def save_send_queue_to_disk():
        pickle.dump(self.send_queue, open(self.local_send_queue_file, "wb"))

    def save_delete_queue_to_disk():
        pickle.dump(self.delete_queue, open(self.local_delete_queue_file, "wb"))

    def find_index_uid_in_folder(self, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=folder)
        typ, data = imaplib.IMAP4_SSL.uid(self, 'SEARCH', "SUBJECT", '"'+INDEX+'"')
        imaplib.IMAP4_SSL.select(self, mailbox=self.selected_mailbox)
        if DEBUG_IMAP_FROM_GMAIL:
            print "found index id", data
        return data[0].split()[0]

    def delete_message_from_actual_folder_uid(self, index_id, folder):
        imaplib.IMAP4_SSL.select(self, mailbox=folder)
        typ, data = imaplib.IMAP4_SSL.uid(self, "STORE", str(index_id), "+FLAGS", r'(\Deleted)')
        if DEBUG_IMAP_FROM_GMAIL:
            print "delete response", typ, data
        typ, response = imaplib.IMAP4_SSL.expunge(self)
        if DEBUG_IMAP_FROM_GMAIL:
            print "expunge response", typ, response
        imaplib.IMAP4_SSL.select(self, mailbox=self.selected_mailbox)

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
        table = json.loads(decrypted_index_body_text[0][1].strip())
        if table[SEQUENCE_NUMBER] < self.last_index_number:
            self.rollback_detected = True
            return self.mapping
        return table

    def fetch_and_load_index(self, index_id):
        imaplib.IMAP4_SSL.select(self, mailbox=CRYPTOBLOBS)
        # fetches the text of message with id index_id
        typ, data = imaplib.IMAP4_SSL.uid(self, "FETCH", index_id, '(BODY[TEXT])')
        # TODO: decrypt message
        imaplib.IMAP4_SSL.select(self, mailbox=self.selected_mailbox)
        # TODO: check index integrity
        # TODO: combine with self.mapping
        # this is probably a race condition
        return self.unpack_index_contents(data)

    def decrypt_and_validate_updated_index(self, encrypted_index_body):
        # TODO: decrypt body
        decrypted_index_body_text = encrypted_index_body

        changed_table = self.unpack_index_contents(decrypted_index_body_text)
        if changed_table[SEQUENCE_NUMBER] < self.last_index_number:
            return False # detect rollback
        self.last_index_number = changed_table[SEQUENCE_NUMBER]
        # save to the local store
        self.save_index_sequence_number_to_disk()
        self.mapping = changed_table
        return True


    def encrypt_and_append_message(self, message):
        message['ORIGINAL-FOLDER'] = self.selected_mailbox
        new_body = str(message)
        # TODO: encrypt message
        self.append_encrypted_message(new_body)

    def append_encrypted_message(self, encrypted_message_body):
        message = Message()
        message['Subject'] = ENCRYPTED
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        message.set_payload(str(encrypted_message_body))
        typ, data = parent.append(self, CRYPTOBLOBS, None, None, str(message))

    def decrypt_and_unpack_message(self, message):
        old_message_str = message.get_payload()
        # TODO: decrypt old_message_str
        return old_message_str

    # pushes up the index to the cryptoblobs folder
    def append_index(self, table):
        message = Message()
        message['Subject'] = INDEX
        message['From'] = "foo@bar.com"
        message['To'] = "foo@bar.com"
        message.set_payload(json.dumps(table)+"\n")
        # TODO: encrypt message
        typ, data = imaplib.IMAP4_SSL.append(self, CRYPTOBLOBS, None, None, str(message))
        if DEBUG_IMAP_FROM_GMAIL:
            print "append_index", typ, data

    def save_index_sequence_number_to_disk():
        pickle.dump(table[SEQUENCE_NUMBER], open(self.local_store_file, "wb"))

    # assumes cryptoblobs and index already exist
    def save_index(self, table):
        index_id = self.find_index_uid_in_folder(CRYPTOBLOBS)
        if DEBUG_IMAP_FROM_GMAIL:
            print "old index id", index_id
        # get information from old index
        self.mapping = self.fetch_and_load_index(index_id) 
        # delete original index
        self.delete_index()
        # increment the sequence number
        table[SEQUENCE_NUMBER] = table[SEQUENCE_NUMBER] + 1
        # save the new sequence number to disk
        self.save_index_sequence_number_to_disk()
        # append new index        
        self.append_index(table)

    def create_cryptoblobs_or_load_index(self):
        if self.mapping != None:
            return
        typ, data = imaplib.IMAP4_SSL.list(self)
        names = [line.split()[-1].strip('"') for line in data]
        # create cryptoblobs folder if one does not yet exist
        if not CRYPTOBLOBS in names:
            if DEBUG_IMAP_FROM_GMAIL:
                print "creating cryptoblobs"
            imaplib.IMAP4_SSL.create(self, CRYPTOBLOBS)
            self.append_index({SEQUENCE_NUMBER: 1})
        # unload the index
        index_id = self.find_index_uid_in_folder(CRYPTOBLOBS)
        self.mapping = self.fetch_and_load_index(index_id)
        if DEBUG_IMAP_FROM_GMAIL:
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
        if DEBUG_IMAP_FROM_GMAIL:
            print "list", data
        return typ, data

    def noop(self):
        if DEBUG_SCHEDULER:
            print "noop", self
        self.create_cryptoblobs_or_load_index()
        typ, data = imaplib.IMAP4_SSL.noop(self)
        # print "noop", data
        return typ, data

    # switches which mailbox we're prodding for updates in
    def select(self, mailbox='INBOX', readonly=False):
        self.create_cryptoblobs_or_load_index()
        self.selected_mailbox = mailbox.strip('"')
        typ, data = imaplib.IMAP4_SSL.select(self, mailbox, readonly)
        if DEBUG_IMAP_FROM_GMAIL:
            print "select", mailbox, data
        return typ, data
    
    def timed_imap_exchange(self):
        # restart timer
        # threading.Timer(DT, self.timed_imap_exchange).start()
        # do things
        if DEBUG_SCHEDULER:
            print "imap timer tick"

        if self._scheduler.next_time_point_action_is_push():
            # push up message
            self.push_up_next_message()
        else:
            # pull down (delete) message from imap
            self.pull_down_next_message()
            # pleeeease don't forget to call create_cryptoblobs...

    def fake_message_created_with_id(uid):
        if not FAKE_MESSAGES in self.mapping:
            self.mapping[FAKE_MESSAGES] = []
        self.mapping[FAKE_MESSAGES].append(uid)
        self.save_index()

    def fake_message_deleted_with_id(uid):
        self.mapping[FAKE_MESSAGES].remove(uid)
        self.save_index()

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
            folder = CRYPTOBLOBS
            # will contain a "message is fake header"
            message_contents = fake_message_with_random_contents_as_string()
            uid = uid_for_constructed_message(message_contents)
            # append onto index's list of fake messages
            self.fake_message_created_with_id(uid)

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
            self.save_index() # this will sync the index to make sure
                              # we know about all fake messages
            if FAKE_MESSAGES not in self.mapping \
                or len(self.mapping[FAKE_MESSAGES]) == 0:
                if DEBUG_SCHEDULER:
                    print "no fake messages to pull down"
                return
            delete_uid = random.choice(self.mapping[FAKE_MESSAGES])
            self.fake_message_deleted_with_id(delete_uid)

        self.create_cryptoblobs_or_load_index()
        self.delete_message_from_actual_folder_uid(delete_uid, CRYPTOBLOBS)
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
    def add_message_to_folder_internal(self, message_contents, folder,
        uid, schedule_upload):
        if DEBUG_IMAP_FROM_SMTORP:
            print "add_message_to_folder", self, "schedule for later", schedule_upload
        if schedule_upload:
            # place it on the queue, deal with it later
            # if messages aren't sent, they'll be pickled and sent next time
            self.send_queue.append((message_contents, folder, uid))
            self.save_send_queue_to_disk()
            return
        # update it in the index
        if DEBUG_IMAP_FROM_SMTORP:
            # print "message_contents", message_contents
            print "folder", folder
            print "uid", uid
            print "host", self.host
            print "port", self.port

        self.create_cryptoblobs_or_load_index()

        if not folder in self.mapping:
            self.mapping[folder] = []
        self.mapping[folder].append(uid)

        # save the index
        self.save_index(self.mapping)

        # turn it into a Message object
        messageified = Message(message_contents)

        # reupload message to the cryptoblobs folder
        self.encrypt_and_append_message(messageified)

    # asks for and receives email
    # command=SEARCH returns a list of the uids in the current mailbox
    # command=FETCH fetches a specific message?
    # it can also be SORT and THREAD.
    def uid(self, command, *args):
        self.create_cryptoblobs_or_load_index()
        typ, data = imaplib.IMAP4_SSL.uid(self, command, *args)
        # print "got data", data
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
            # TODO: actually handle case where this is the index that's been
            # updated by another client
            message_contents = data[0][1].strip()
            messageified = Message(message_contents)
            subject = messageified['Subject'].strip().strip('"')
            if DEBUG_IMAP_FROM_GMAIL:
                print "subject", subject
            if folder == CRYPTOBLOBS or subject == ENCRYPTED or subject == INDEX:
                if DEBUG_IMAP_FROM_GMAIL:
                    print "probably not a real message"
                # this could be the index, which means that
                # another client has updated the index
                if subject == INDEX and folder == CRYPTOBLOBS:
                    # TODO currently ignoring index updates, because we're
                    # the ones who made them. change for multiple clients.
                    return False, []
                    if DEBUG_IMAP_FROM_GMAIL:
                        print "found the index", data
                    # 
                    # deal with the changed contents of the index?
                    # for now, just copy the index into the local store
                    # the scan will just give us the updated messages in cryptoblobs
                    ok = self.decrypt_and_validate_updated_index(messageified.get_payload())
                    # not sure we currently actually have to deal with changes in the index
                    # this is a fantastic UI choice.
                    if ok:
                        messageified.set_payload("Everything is awesome.")
                    else:
                        messageified.set_payload("Everything is not awesome.")
                    data[0][1] = str(messageified)
                    # it's probably fine to just have this ui component here,
                    # because it means the server has updated it, and wants us
                    # to grab the rolled back one.
                elif subject == ENCRYPTED and folder == CRYPTOBLOBS:
                    # returns a string
                    # TODO we need to know if we're the ones who just put this there.
                    # if so, ignore for now, maybe change this later.
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

    def open(self, host = '', port = IMAP4_SSL_PORT):
        a = imaplib.IMAP4_SSL.open(self, host, port)
        # print "opening mailbox", host, port
        return a    

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


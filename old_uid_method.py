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
    # TODO: return fake information
if DEBUG_IMAP_FROM_GMAIL:
    print "uid", command#, _parse_imap(a)
# _parse_imap will only work when it's not FETCH.
# from mailbox import Mailbox, Message
#Message(data)
#if 
# print "returning data", data
        return typ, data
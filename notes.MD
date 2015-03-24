	## to test
- what if a filter's set up and it comes in that way?
- you know actually run with multiple clients

## big remaining todo steps
- implement workflow when coming from a secure source
- delete from all mail, in addition to inbox
- don't re-fetch message that I just pushed to cryptoblobs
- implement scheduler and updates on schedule
- have all functionalities operate on that schedule

## some notes
- assuming that all IMAP clients are running the protocol
- possible TODO: figure out what it looks like when something on the server was changed by another imap client.
- input on encryption method?
- opportunistically add messages to index
- http://pymotw.com/2/imaplib/
- https://docs.python.org/2/library/imaplib.html
- https://tools.ietf.org/html/rfc3501#section-6.4.4
- https://docs.python.org/2/library/email.message.html#email.message.Message

## 2/25/15
- mailpile selects folder instead of passing into uid, so make sure to
handle both types of selection.
- VICTORY VICTORY IT'S DELETING AND REUPLOADING INTO THE OTHER FOLDER

## to bring up in meeting
- so, mailpile doesn't actually reflect local changes on the server. like
  if I added it to a local folder or something, it doesn't care. so if I actually
  made it so such changes were reflected in the imap stuff, I couldn't test it
  without significantly changing mailpile as well...
 - added rollback detection. unsure if that made it recrash or I just found an original bug??

## notes from meeting 2/26/15
- forward security
- index --> size
- fine to know it exists
- currently can see when a message was created
- time it would have come from
- my mission: enabling a secure client to use imap at all
- want all functions and show that it works so mailpile, for example, can use it
- in the case of captured imap server + SMTorP or network + legacy IMAP:
- we don't want the adversary to know when we've received a message
- so: algorithm based on the state of the system sends some information per unit time, informing a planning component of a schedule for ups and downs
- by ups and down: either download k messages and upload k+1, or the reverse.
- so how often, and how many messages. this way we can hide received messages in there, and also delete messages off of the server.
- note that this is planned with SMTorP/untrusted imap in mind. network/legacy should not be a priority in planning.

### todo from 2/26
- implement scheduler and updates on schedule
- have all functionalities operate on that schedule

### notes 3/3
- http://imapwiki.org/ImapTest/ServerStatus
-- most servers do not implement the entire protocol

# notes from 3/10ish
- I found where it's stored. it's .local/share/Mailpile/.
- all mail is just wonky. it's not me. it shows 2 when it should show all? It doesn't copy messages into all mail that are elsewhere?
- holy inconsistencies, batman: "If you delete a message from your inbox or one of your custom folders in your IMAP client, it will still appear in [Gmail]/All Mail.

Here's why: in most folders, deleting a message simply removes that folder's label from the message, including the label identifying the message as being in your inbox. [Gmail]/All Mail shows all of your messages, whether or not they have labels attached to them. If you want to delete a message from all folders, move it to the [Gmail]/Trash folder.

If you delete a message from [Gmail]/Spam or [Gmail]/Trash, it will be deleted permanently."
- ok, changed the settings on the server to do the REASONABLE thing.
- that is, auto-expunge off, and deleting actually deletes. who knew you needed to
tell it to do that explicitly? asdajfasdf.
- so the index contains messages from cryptoblobs, which is probably what's causing the triple-index problem.
- EVERYTHING IS CRASHING BECAUSE OF SOME EXTRA QUOTES AND JSON.

## to bring up in next meeting
- scrap network/legacy model. it's not what we're planning for at all.

## notes from 3/23
- When a message is marked as deleted and expunged from the last visible IMAP folder: Immediately delete the message forever
- how to solve my problems, temporarily: set up a rule in receiving gmail to have all messages skip the inbox and go directly to all mail. because you know what I am done dealing with this and have to move on.
- this doesn't fix the problem of keeping the last three indices. why is that happening.
- FOUND THE PROBLEM. ok so what's happening is that the message is removed from the cryptoblobs folder, but not all mail, so it still exists. then another message appears with the same subject. this will be threaded with the previous message, which will be BROUGHT OUT OF ALL MAIL AND GROUPED WITH THE NEW ONE AND HAVE THE LABEL REAPPLIED TO IT. I'm just turning off threading. YEP THAT SOLVES EVERYTHING.
- https://support.google.com/mail/answer/78755
- https://support.google.com/mail/answer/77657?hl=en
- ok, so here's the thing. this is super gmail-dependent. because if I want to actually delete from all mail, I have to move to trash, then delete from trash. that's the only gmail way to do it. as opposed to a PROPER, NORMAL, NON-MALICIOUS server that doesn't have weird unspecified behaviors. so you know what, the old indices are just going to stay in all mail for now. because I have other things to do.
- actually, I think I have it mostly set up so the code is generic, and changes are made in gmail. maybe.
- possible todo: check what happens when message is there before index is thrust upon it.
- setting up smtorp.
- this means setting up tor as a hidden service. that's putting these lines into the torrc file:
HiddenServiceDir /home/user/.local/share/tor/hidden_service/
HiddenServicePort 25 localhost:33412
- note, needed to create that folder before it was happy.
- https://github.com/mailpile/Mailpile/wiki/SMTorP#proof-of-concept this is the sort of fun documentation I get to enjoy.
-   def _is_dangerous_address(self, address):
        return False  # FIXME

    def _is_spam_address(self, address):
        return False  # FIXME
- well that's one way to handle spam detection on encrypted data.
- but what is the user name.
- irc is a dead zone.
- https://github.com/mailpile/Mailpile/wiki/SMTorP
- https://github.com/mailpile/Mailpile/commit/eeb315cbd831777902fc8ff9a33fe570e2093987
- https://github.com/mailpile/Mailpile/commit/eeb315cbd831777902fc8ff9a33fe570e2093987
- https://github.com/mailpile/Mailpile/commit/bdc8d92ad8b21219e28ce8e16f6b74dfded1d579


## notes from meeting 2/17/15
### Threats
- "oblivious RAM"
- reupload how many
- what can we at a time guarantee
- traffic analysis
- deleting correlation
- consider the boxes

### Adding a new client
- need existing device when setting up new one twenty ??? or from password
- DH over header
- type in thing you see
- encrypt UID into contents so you know it's the message you asked for

### Rollback
- keep version number of index
- index contains a table of id --> hash ciphertext, is associated with a particular state of the system
- no reason to change blob without changing index
- every time you update, increase version number in index
- (something that's probably good to handle although I may not) pull before you push/ multiple clients acting simultaneously

### Measurements
- size of data structures
- function of messages, size
- performance, how many touched,
- how many messages sent back and forth
- total IMAP storage
- bulk move --> factor

### Ciphertext
- plaintext
- cost of packetization vs. pkt size
- cost, storage vs. how big to make packets
- how big are my personal real messages?
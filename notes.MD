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

# notes from 3/10
- I found where it's stored. it's .local/share/Mailpile/.
- all mail is just wonky. it's not me. it shows 2 when it should show all? It doesn't copy messages into all mail that are elsewhere?
- holy inconsistencies, batman: "If you delete a message from your inbox or one of your custom folders in your IMAP client, it will still appear in [Gmail]/All Mail.

Here's why: in most folders, deleting a message simply removes that folder's label from the message, including the label identifying the message as being in your inbox. [Gmail]/All Mail shows all of your messages, whether or not they have labels attached to them. If you want to delete a message from all folders, move it to the [Gmail]/Trash folder.

If you delete a message from [Gmail]/Spam or [Gmail]/Trash, it will be deleted permanently."

## to bring up in next meeting
- scrap network/legacy model. it's not what we're planning for at all.

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
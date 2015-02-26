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
- VICTORY VICTORY IT'S DELETING AND REUPLOADING INTO THE OTHER FOLDER FUCK YEAH

## to test
- what if a filter's set up and it comes in that way?
- you know actually with multiple clients

## big remaining todo steps
- implement workflow when coming from a secure source
- delete from all mail, in addition to inbox
--- no seriously deal with all mail, this is a big problem.

## to bring up in meeting
- so, mailpile doesn't actually reflect local changes on the server. like
  if I added it to a local folder or something, it doesn't care. so if I actually
  made it so such changes were reflected in the imap stuff, I couldn't test it
  without significantly changing mailpile as well...
 - added rollback detection. unsure if that made it recrash or I just found an original bug??

## notes from meeting during the second to last week in February
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
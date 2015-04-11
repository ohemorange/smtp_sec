## where are the methods?
- smtp_server: smtpserver: processmessage
- imapmailsource:add_side_message
- imap_sec: add_message_to_folder
- mailutils: prepare message

## to test
- what if a filter's set up and it comes in that way?
- you know actually run with multiple clients

## todo
- subject lines: random string. doesn't need to be saved because you can tell
  as new client.
  - cool but not necessary: a string that's possible in imap but not smtp
- handle key management
- solve the multi-client systems problem - index as a log or a lock. Your
  Favorite Method, really.
  - then every t, delete log, because you don't want deleted messages saved.
- figure out if imap is running over ssl or the other way around in imap_ssl
  (I think it's the former)
- maybe pull pack to gmail folder and such if it's gone over smtorp.
- pickle and load the send-to-imap-from-smtorp queue.
- switch from pushing and pulling single messages to pushing up k and pulling down k-1
- add functionality for delete and change folders
- when a new message comes in, if it's the index and a new version, update
  based on that. this will ensure that we always have the most recent 
  version.
- up by putting up k and down k-1. (mixing step)
- add local_store_file in mailpile. also local delete and send queue files.
- think through what happens when we're the second client to sign up
  - the server should not be able to sign up as a client
- deal with the nonsense going on in unpack_index_contents, fetch_and_load_index, and decrypt_and_validate_updated_index.

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
 - most servers do not implement the entire protocol

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

## notes from meeting 3/24/15
- include short section on policy, including third party doctrine
- appendices: weird stuff in gmail, mailpile
- dissemination: within an organization. they usually have to download special software anyway.
- key management:
 - problems with passphrase-based encryption
 - what if they forget the password. you could do it so it's either password or device,
   but users tend to not like it if you can't do the thing you told them you wouldn't
   be able to do.
- subject lines: random string. doesn't need to be saved because you can tell as new client.
 - cool but not necessary: a string that's possible in imap but not smtp
- how to test:
 - telnet to smtp server
 - hello, then ask for names
 - try delivering to username, ask for hosts
 - ask for addresses
- append to todo list:
 - handle key management
 - multi-client systems problem - index as a log or a lock. Your Favorite Method, really.
  - then every t, delete log, because you don't want deleted messages saved.

## notes from 3/30
- no no I see nothing wrong with writing protocols that only talk to themselves
  - anyway, the format is:
    - MAIL FROM: eportnoy@princeton.edu
    - RCPT TO: ebportnoy@gmail.com
    - RCPT TO: ebportnoy@gmail.com##239-1
    - use calc_collision.py
- guess who found another bug. it's me. did they even run this code?
    def smtp_DATA(self, arg):
        print "smtp_DATA", arg
        if self.is_spam:
            self.push("450 I don't like spam!")
            self.close_when_done()
        else:
            smtpd.SMTPChannel.smtp_DATA(self, arg)

   put prints around this stuff:
   # Update the in-memory-index
   mi = self.get_msg_info()
   mi[self.index.MSG_PTRS] = newptr
   self.index.set_msg_at_idx_pos(self.msg_idx_pos, mi)
   self.index.index_email(session, Email(self.index, self.msg_idx_pos))
- smtp_ssl = proto in ('smtpssl', )  # FIXME: 'smtorp'
- I think the address might be foo@, something flashed by.
-             if rcpts[0].lower().endswith('.onion'):
                return {"protocol": "smtorp",
                        "host": rcpts[0].split('@')[-1],
                        "port": 25,
                        "username": "",
                        "password": ""}
- compose:Sendit calls mailutils:preparemessage, then smtpclient:sendmail
- ok so I FINALLY got their code working. no one has ever run this code.
  it freaks out when smtorp has two recipients, but hey GUESS WHAT THE
  COMPOSE CODE DOES. it adds the sender as a second recipient is what it
  does. and don't get me started on the bcc code. this nightmare is in
  preparemessage, in mailutils. anyway, it's working now. who needs to send
  it to yourself.
- smtp_server: smtpserver: processmessage --> imapmailsource:add_side_message -->
  imap_sec:	add_message_to_folder
- when deleting all local data, make sure to set port number. the plugin is
  already appended.
- 173.194.206.109: google
- 140.180.254.66: me
- https://www.bearfruit.org/2008/04/17/telnet-for-testing-ssl-https-websites/


## notes from week of 4/4
- why is it working? oh please don't make me look into play_nice_with_threads().
  - it's in a try/catch block, which makes me think there's someone out there who
    knows PERFECTLY WELL what nonsense is going on here.
  - let's see who calls process_message.
    - ????????????? NO ONE CALLS IT?????
    - ok no other class seems to be calling SMTPServer, which it's in???
    - maybe it's using plugins to replace smtpd. because mailpile-test uses a
      different port number for smtpd. I'm not sure I buy this.
    - ok so the plugin manager loads the file. that is the setup we have here.
    - and then we register a worker and command. a worker has a start and a quit.
    - ok we're using generics here. so an SMTPServer subclasses the python
      smtpd.SMTPServer, and process_message is something that like just happens
      with that. so the server's running, it catches incoming messages, and we
      just change the processing. which means that the problem might be in how it's
      configured. or it could be my personal python's version of SMTPServer which
      is outdated.
    - http://pymotw.com/2/smtpd/
- ssl handshake
  - 10.8.90.153 to 54.68.169.172: hello, version TLS 1.0
  - 54 to 10: server hello, version TLS 1.2
  - 54 to 10: certificate
  - 10 to 54: client key exchange, change cipher spec, hello request, hello request
  - 54 to 10: new session ticket, change cipher spec, encrypted handshake message
  - 54 to 10: spdy
    - spdy is not http.
- another ssl handshake
  - 10.8.90.153 to 173.194.121.52:
    - so the outer layer says 1.0, but the handshake itself says 1.2?
- so the client hello claims to be running 1.0, but initiates a 1.2 handshake.
  guess I should probably check out that RFC. look at tls_version.png.
- current framework only accounts for up and down, not move. that is a
  combination, but it should definitely be there.
- the index probably shouldn't be on the same schedule as everything else.
- _plugins.register_config_variables('prefs', {
    'empty_outbox_interval': [_('Delay between attempts to send mail'),
                              int, 90]
  })
  - from mailpile/plugins/compose.py
  - so outgoing is batched anyway. that's the other end of things, anyway.
- don't forget to start tor, sweetie...
- so. I probably have to actually fix the tls version problem. I figured out
  how to do that, found a nice patch for it. a patch. for the source. which I
  will now be attempting to build python from. I'm excited. see PEP 466
- better idea! "just" go into /usr/lib/python2.7, and change all the defaults
  in ssl.py to use PROTOCOL_TLSv1_2. anyway, we can probably pass that as a
  parameter in the application.
  - tried that. doesn't change anything??? someone else is calling this guy
    and not setting defaults. could be another python guy. maybe imaplib or
    SMTPServer.
  - yeah, it's in imaplib. on the bright side, I found one place to hook in
    and fix things instead of having to do it at every point in ssl.py...
- we were talking to 64.233.171.108 (definitely imap)
  - then we started talking to 74.125.22.109 (pretty sure this is also imap)
- try this: grep -r "mail_sources" .
- so. what I'm currently trying is putting the dequeue code in noop.
  - because it's called every 120 second (although it seems to actually be 
    going faster than that, but that's not a big issue). I could also just
    call the "timed imap" method or whatever. it seems to be working now. a
    thing to make sure is that the same instance it's enqueued on is the one
    it's pushed from. I could handle this with saving it down and bringing it
    up, that's probably better anyway. I'll put that in the todo. once I test
    this a bit more. it should be the same instance tbh, because I'm just
    grabbing it from the context. the problem was when I was calling new 
    threads of myself and such.
    - forget this. I'm keeping it in noop. because this lets mailpile do
      WHATEVER STRANGE NONSENSE it wants with making methods part of other
      classes and proxying and I am just NOT dealing with that.
      - I should still pickle the queue, though.
- current task: figure out why noop is getting called so often. and how to 
  time for things for the scheduler.
- OK. SO.
  - in mail_source/__init__, BaseMailSource has a run method. this run
    method calls sleeptime(), which returns 300 from self.my_config.interval,
    which is loaded from somewhere.
  - I'm guessing ./mailpile/www/default/html/jsapi/setup/sources.js
  - NOW. if !(self._last_rescan_completed or self._last_rescan_failed), then
    sleeptime just returns 1. I'd be willing to bet those never complete
    because I'm just throwing things out when I'm rescanning. so to handle
    this properly, I should add another flag or something. but instead, I'm
    just having it always return self.my_config.interval. because whatever.
  - anyway, this means that now BaseMailSource.run is called every 300
    seconds. This calls ImapMailSource.open, which calls noop as just part
    of its stuff to test things or whatever.
  - so then we also have ImapMailSource.run, which has some funky idle code
    or whatever, but I'm pretty sure it's called every 120 seconds. this is
    just hardcoded in there. there being mail_sources/imap.py. anyway, every
    120 seconds, it calls noop to keep the connection alive and such. now
    unfortunately, the way it calls noop is convoluted and strange and
    involves some proxying something or other.
  - so the best thing to do is probably to put a second call in the 120-
    second run loop, to timed_imap_exchange. this means figuring out their
    way to call things. I'd rather keep it in noop, but that could be called
    whenever and it's really best to keep things on schedule. it's probably
    best to let the caller handle it. actually, we could have 
    timed_imap_exchange take in a number of seconds since it was last called,
    and calculate what to do based on that. and if I want to be janky about
    it, I could have noop itself keep track of when it was last called, and
    continue calling from noop. that's messy but would theoretically work.
  - or, if I want to be super duper janky, I can just keep calling
    timed_imap_exchange from noop. and have it called every 120 and every 300
    seconds and just deal with it, because it's pretty fuzzy.
    - this is wrong and I totally should not do this.
  - I should also mention, while I'm here: an ImapMailSource inherits from a
    BaseMailSource, which is a Thread. it is instantiated by calling
    MailSource, and which one it is is based on my_config.protocol. this code
    is at the bottom of mail_source/__init__.
- I used this "who called me" code for debugging: http://stackoverflow.com/questions/2654113/python-how-to-get-the-callers-method-name-in-the-called-method


## notes from meeting 4/8
- on init, promise to call the scheduler every time t, then do it.
- possible todo: have imap_sec set the "everything worked" flags and actually
  go back to checking them, instead of just always doing every 300 seconds
  and never immediately retrying on fail.

## notes from week of 4/8
- translating it to calling the method directly after the noop was
  surprisingly easy, it just like worked with the setattr mechanism? I
  also pass in a parameter of how often the tick is called, in the
  constructor.
- fake message contains a "message is fake" header
- using python to interface with gmail
  - https://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/
- pushing and pulling up only one at a time: stop network timing attacks.
- pushing and pulling a set: stop attackers with access to the imap server
- by the way, IMAP4_SSL's open method creates a socket, then wraps the
  socket in ssl.
- I should make sure index saves are consistent across all timed actions,
  because otherwise that's a side channel.
- scheduling algorithm 1: 6 up, 4 down. 1 per time stamp.
- WAIT. is there any reason to bring up and down multiple per tick? I'm
  pretty convinced there's not.
  - no, there is. assume you have 2x the number of messages pushed up as
    actually exist. over time, for a given message, the probability of a
    real message being deleted is 0, but the probably of a fake message
    being deleted tends towards 1 (because the probability of it being
    selected on any time tick is p < 1, the probability of it not being selected is 1 - p = q < 1, and so the probability of it never being
    selected is q^n, and q^infinity is 0, so it will be selected at least
    once).
- by the way, pond randomizes times since it's not always communicating with
  the same server. because to send a message, it connects to the recipient's
  server.
- metadata-free multi-client email storage. hiding metadata drom an imap
  server for metadate-secure transport mechanisms.
- we can't do the pond thing because we're hiding from the server, not just
  a network observer.
- added pickling sequence number. this means that the constructor has to
  now pass in a file where it'll be saved. this should be per mailbox, in
  mailpile. hm. this will fail silently. hope that's not too big of a
  problem.
- we are now pickled and depickling send and delete queues. need to call
  with file in mailpile.
- **** should send on next tick probabilistically? because if they're in
  the imap server and also watching the network, they'll know which one
  in the server it is. well not if I mix it. but still they'll know it's
  in the batch. discuss. todo.
- just have FAKE_MESSAGES be a folder name. and then if we ever translate
  down from the index, will have to just ignore that or something.
- calling create_cryptoblobs at the end of login. this means that we should
  never be logged in without it having been created. should be fine?
- COOL fixed up a bunch of synchronization stuff. mainly with fetching and
  saving the index. I'm not repeating myself, just look at the code, it's
  commented.
- we're going with bcrypt/passphrase.
  - which means we should probably have a method for "delete everything 
    and start over." which honestly would have made my life easier all
    this time but whatever.
  - we could also encrypt the local stuff with the key derived from the
    passphrase. don't think it matters too much though tbh.
-  > If (1), I'd suggest Scrypt(hash=HChaCha20, kdf=Shake255)
  - David Leon Gil, email to messaging@moderncrypto.org
  - ok, so the best practice would be to store the salt somewhere. we'll
    call that a TODO.
- not-going-to-happen-todo: use a different string equals to prevent
  timing attacks
  - http://rdist.root.org/2010/01/07/timing-independent-array-comparison/
- using crypticle - no more noop encryption! yay!


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
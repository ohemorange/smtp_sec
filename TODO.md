1. modify mailpile to do something when there's something.


- understand how mailpile works
- python hooks into pond

so it's like a pond-diverting plugin in thunderbird


- what if the client encrypts the traffic completely??? I'd have to mitm wouldn't I... so it does require being part of the client. I'm pretty sure.
Two options:
1. Hook into the client, before it encrypts and sends over smtp
2. MITM the client's smtp traffic

Pro of 1: Cleaner, not MITMing, not re-smtping, can use the client's address book
Pro of 2: Outside the client.

Ok, I should figure out how to send programmatically through Pond.

## Create a proxy

- Fork Mailpile and Pond
- Set up Mailpile to point to a local proxy instead of directly to server

## Syncing to IMAP

- When the proxy receives an email with a particular subject line:
Move headers to message content
Replace headers with default/junk values
Move message to specific folder
Delete original message
Make sure these changes sync

Sending through Pond

Integrate Pond into proxy
Set up two instances of Pond (?)
When an email is sent with a particular subject line:
Move headers to content
Put in Pond’s format
Send over Pond
When a message is received on a Pond instance
Unbox it into the mail program’s format
Sync it in with the cryptoblob folder

Integrating new and old mails

Get messages stored in the cryptoblob folder to synchronize with the local client’s index
Switch recognition of newmail messages/ newmail capability from subject line to SMTP header
Add UI element to indicate extra-super-special protection
Automatically switching to newmail
When we see a “newmail-capable” header in an email, mark it in the contact card.
Key management
Set up some automatic system for key management. Either Pond’s or Coniks’ or Mailpile’s (but automatic).
Multiple devices
Add a scheme for viewing the same encrypted messages from different devices
Password-enabled recovery
Optionally, have key based on a password so a user can log in and see all files.
Paranoid mode
Implement out-of-band discovery option to avoid handshake through legacy mail

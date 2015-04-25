from imaplib import *
from getpass import getpass

imap = IMAP4_SSL("imap.gmail.com",993)

password = getpass()

imap.login("ebportnoy",password)
imap.select("[Gmail]/All Mail")

typ, data = imap.uid("SEARCH",None,"ALL")

uids = data[0].split()
new_uids = uids[18191:]

dates = []
for uid in new_uids:
	typ,data = imap.uid("FETCH",str(uid),"(BODY[HEADER.FIELDS (DATE)])")
	dateline = data[0][1].strip()
	dates.append(dateline)

dates = all_datestrings
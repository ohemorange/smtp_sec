from imaplib import *
from getpass import getpass
import pickle

imap = IMAP4_SSL("imap.gmail.com",993)

password = getpass()

imap.login("ebportnoy",password)
imap.select("[Gmail]/All Mail")

typ, data = imap.uid("SEARCH",None,"ALL")

uids = data[0].split()
new_uids = uids[10000:]

dates = []
for uid in new_uids:
	typ,data = imap.uid("FETCH",str(uid),"(BODY[HEADER.FIELDS (DATE)])")
	dateline = data[0][1].strip()
	dates.append(dateline)

filenames = ['18191dates.pkl', 'next10k.pkl', \
		     'thirdbatch.pkl', 'fourthbatch.pkl', 'fifthbatch.pkl']

all_datestrings = []
for filename in filenames:
	file = open(filename, "rb")
	dates = pickle.load(file)
	file.close()
	all_datestrings = all_datestrings + dates

# new start: 71672
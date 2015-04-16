from imap_sec import *
i =  IMAP4_SSL("secret","imap.gmail.com",993)
i.login("functorkitten","ocamldavewalker")

i.select("INBOX")
i.uid("SEARCH",None,"ALL")
i.uid("FETCH","185","(BODY[TEXT])")

i.select(mailbox="[Gmail]/All Mail")
i.uid("SEARCH",None,"ALL")
i.uid("FETCH",820,'(BODY[])')


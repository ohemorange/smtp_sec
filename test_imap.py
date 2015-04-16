from imap_sec import *
i =  IMAP4_SSL("secret","imap.gmail.com",993)
i.login("functorkitten","ocamldavewalker")

i.select("INBOX")
i.uid("SEARCH",None,"ALL")
i.uid("FETCH","185","(BODY[TEXT])")

i.select(mailbox="[Gmail]/All Mail")
i.uid("SEARCH",None,"ALL")
i.uid("FETCH",820,'(BODY[])')


for i in range(0, len(data)):
    if CRYPTOBLOBS in data[i]:
        delete_index = i
        break


for folder in i.mapping.keys():
    # search through lines in data
    if folder == SEQUENCE_NUMBER or folder == FAKE_MESSAGES:
        continue	
    found = False
    for line in data:
        if folder in line:
            found = True
            break
    if not found:
        to_append.append(folder)

for folder_name in to_append:
    string = before + folder_name + after
    data.append(string)
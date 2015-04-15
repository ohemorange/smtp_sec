actual message lock probz
delete_message_from_actual_folder_uid 840 [Gmail]/All Mail
selecting mailbox "[Gmail]/All Mail"
selected folder OK ['3']
delete response OK ['3 (FLAGS (\\Deleted) UID 840)', '3 (UID 840 FLAGS (\\Deleted))']
expunge response OK ['3']
selecting mailbox "[Gmail]/All Mail"
folder [Gmail]/All Mail
uid 840
host imap.gmail.com
port 993
trying to acquire index lock
selecting mailbox "CRYPTOBLOBS"
find_lock_uid_in_folder folder CRYPTOBLOBS
find_lock_uid_in_folder OK ['2']
selecting mailbox "[Gmail]/All Mail"
found lock id ['2']
delete_message_from_actual_folder_uid 2 CRYPTOBLOBS
selecting mailbox "CRYPTOBLOBS"
selected folder OK ['2']
delete response OK ['2 (FLAGS (\\Deleted) UID 2)', '2 (UID 2 FLAGS (\\Deleted))']
expunge response OK ['2']
selecting mailbox "[Gmail]/All Mail"
fetch_and_load_index
selecting mailbox "CRYPTOBLOBS"
find_index_uid_in_folder folder CRYPTOBLOBS
find_index_uid_in_folder OK ['1']
selecting mailbox "[Gmail]/All Mail"
found index id ['1']
selecting mailbox "CRYPTOBLOBS"
selecting mailbox "[Gmail]/All Mail"
subject_data [('1 (UID 1 BODY[HEADER.FIELDS (SUBJECT)] {29}', 'Subject: INDEX 5644623516\r\n\r\n'), ')']
stripped Subject: INDEX 5644623516
save_salt_and_related_information 5644623516
saved salt and related information.
key_derived_from_passphrase secret 5644623516
self.encryption_key @x��P1N��L���&h/�'����!�C��1(!�s�=��3}���)0�	m�U��4�����
crypt created perfectly well <crypticle.Crypticle object at 0x7f4f58192790>
out {"SEQUENCE_NUMBER": 1}
decryption succeeded
unpack_index_contents {"SEQUENCE_NUMBER": 1}
selecting mailbox "INBOX"

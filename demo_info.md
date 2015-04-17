
rm -rf ~/.local/share/Mailpile/
rm ~/.local/share/Mailpile/default/mailpile.in

rescan sources

cat /home/user/.local/share/tor/hidden_service/hostname 


send to:
foo@rwq5q4vh3aphekjj.onion
start tor
set sys.smtpd.port = 33412
restart mailpile

to get smtorp to appear for the first time:
(turn off index refetch cough cough)
gear --> mail sources --> update from there. make take a few seconds
rescan sources

OR:
rm -rf .local/share/Mailpile
(don't forget:)
set sys.smtpd.port = 33412
restart mailpile

turn of fetching of index?

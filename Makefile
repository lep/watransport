PYTHON:=/usr/bin/env python

.PHONY: run cli clean

watransport: __main__.py Account.py Database.py HttpServer.py Jid.py MediaDownloader.py MediaServer.py Stanzas.py XMPPComponent.py XMPPLayer.py
	@echo Making $@
	@zip watransport.zip $^ > /dev/null
	@echo "#!${PYTHON}" | cat - watransport.zip > watransport
	@chmod +x watransport
	@rm watransport.zip

run: transport.db watransport
	@${PYTHON} -u watransport --debug --password=passowrd --transport-domain=transport.wa

transport.db:
	@echo Making $@
	@sqlite3 $@ < schema.sql

clean:
	@rm watransport.log
	@rm watransport

cli:
	@yowsup-cli demos -y -l "${PHONE_NUMBER}:${WA_PASSWORD}"; reset

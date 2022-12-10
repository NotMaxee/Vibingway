#!/bin/bash
cd "$(dirname "$0")"
sudo python3.11 launcher.py
ret=$?

if [ $ret -eq 25 ]; then
	git reset --hard
	git pull
fi

exit $ret

#!/usr/bin/env python
# -*- coding: utf-8 -*-

# remove the 16.xxx spam user
from os import listdir, path
import re
from shutil import move


def action(folder, valid_users, move_to):
    if not path.isdir(folder):
        raise StandardError("no folder: %s" % folder)
    if not path.isdir(move_to):
        raise StandardError("no folder: %s" % move_to)

    USER_FILE_RE = re.compile(r'^[0-9\.]+$')
    for file in listdir(folder):
        if path.isdir(file): continue
        if USER_FILE_RE.match(file) is None: continue
        user_file = path.join(folder, file)
        name = getNameFromUserFile(user_file)
        if name in valid_users:
            print "ok -> %s" % name
        else:
            print "move -> %s" % name
            move(user_file, move_to)


def getNameFromUserFile(file):
    lookingFor = "name="
    with open(file, "r") as file:
        for line in file:
            if line.startswith(lookingFor):
                # remove the newline also
                return line[len(lookingFor):len(line) - 1]

    raise BaseException("No name= entry found!")


def read_valid_users(file):
    u = []
    with open(file, "r") as f:
        for line in f:
            line = line.strip()
            if len(line) > 0:
                u.append(line)

    return u


if __name__ == '__main__':
    action(
        folder="testdata/spammer",
        valid_users=read_valid_users('valid_users'),
        move_to="testdata/spammer/disabled"
    )


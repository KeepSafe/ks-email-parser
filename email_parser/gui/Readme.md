# ks-email-parser gui

This is an extension module to `ks-email-parser` that allows editing emails using a web frontend.  The user may create
new emails based on existing HTML templates, or edit existing emails in the Android XML format.  Emails are read from
and written to the local hard drive where the application is running.

## Goal
The goal is to provide a friendlier interface to make it somewhat easier to generate emails that can be processed
 by `ks-email-parser`.

## Requirements

1. Python 3.+
2. libxml - on OSX install with `xcode-select --install`

## Installation

`make install`

## Usage

`ks-email-parser gui` in root folder.  This will (by default) fire up a local HTTP server on port 8080.  You should
then visit <http://localhost:8080> in a modern web browser to interact with the app.


### Options

Run `ks-email-parser --help` to see available options.  All options for the base `ks-email-parser` can be used to
change the configuration of what folders and files are used for templates, emails, and so on.  In addition, the user
may specify a port other than 8080 by `-P` or `--port`.

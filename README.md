# Vibingway

> **Hey!** I cobbled this project together in a few evenings. As such, a lot of
> the under-the-hood functionality isn't exactly best practice. Regardless,
> I've made some effort to make this easy to set up and use.

Vibingway is a multi-purpose bot with a small set of features intended for small
communities and private servers.

## Installation

A full installation guide is provided in the documentation. To access it, you
will need Python 3.11 or higher and clone the repository.

Once cloned, install the requirements for the documentation using
`pip3 install -r requirements-docs.txt`.`

Then, build the documentation using ``docs/html.bat`` on Windows, or by running
`sphinx-build -b html docs/source docs/build` on Unix systems.

Finally, open ``docs/build/index.html`` for the documentation.

## Features

Vibingway currently offers the following features:

* Play music from various sources supported by Lavalink using ``/music``.
* Add rotating banners to your discord server using ``/banner``.

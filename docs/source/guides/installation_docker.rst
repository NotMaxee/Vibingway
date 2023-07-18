.. _guides_installation_docker:

Installation with Docker
###################

This page features a step-by-step installation guide for the bot using Docker & Docker Compose.

Create a new Discord Bot
************************

First you will have to create a new Discord Bot.

Head to https://discord.com/developers/applications, create a new application
and add a bot user to it.

Head to Oauth2/General and select the following authorization settings:

.. image:: ../_images/guides/oauth_permissions.png

Go to Oauth2/URL Generator, check ``applications.commands``, copy the generated
URL and paste it in your webbrowser to add the newly created bot to a discord
server of your choice.

Prerequisites
*************

* Docker
* Docker Compose

Docker
===========

You can find installation instructions for Docker here:

https://docs.docker.com/engine/install/

Docker Compose
===========

You can find installation instructions for Docker Compose here:

https://docs.docker.com/compose/install/

Setup
************

Clone the repository locally and change into the directory you cloned it into.

Next, create a ``config.py`` file and copy the contents of ``config.example`` into it. You will need to change the following values so that the database and lavalink can connect to each other using the docker network:

.. code::
    database_credentials = dict(
        user     = "postgres",
        password = "vibingway",
        host     = "db",
        port     = "5432",
        database = "vibingway"
    )

    lavalink_credentials = dict(
        host     = "lavalink",
        port     = 2333,
        password = "vibingway"
    )

The credentials will automatically work as these are the default values for the docker-compose setup. These services will not be exposed to the outside world, so you can use these credentials without any worries as long as you don't change the docker-compose setup to expose these services.

Fill in the other values required as usual before continuing.

Running
**************

To start the bot, run the following command:

.. code::
    docker-compose up -d

This will start the bot in the background, do any database migrations, start the lavalink server and ensure it keeps running until you stop it again. Data will automatically be persisted as long as you don't remove the volumes.

To stop the bot, run the following command:

.. code::

    docker-compose down

To stop the bot and remove all data, run the following command:

.. code::

    docker-compose down -v


Updating
**************

To update the bot, run the following command:

.. code::

    git pull && docker-compose pull && docker-compose up -d --build

This will pull the latest changes from the repository, pull the latest images for required services and rebuild the bot with the latest changes.


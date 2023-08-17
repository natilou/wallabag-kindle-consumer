This project is a fork  from [janLo/wallabag-kindle-consumer](https://github.com/janLo/wallabag-kindle-consumer)
Since the original repository has not been maintained, I am now actively maintaining and working to improve it.

# Push tagged wallabag articles to kindle


This is a service that polls a [Wallabag](https://wallabag.org/en)
instance for articles with a certain tag (`kindle`, `kindle-mobi` or
`kindle-pdf`). If it finds an article tagged with one of those tags, it
exports the article in the requested format and sends it via email to a
configured kindle address.

The software consists of three parts:

* **consumer:** This is the part that consumes the tags from Wallabag
  and pushes them to the kindle addresses.
* **refresher:** As Wallabag gives no permanent api tokens we need to
  refresh them regularly. This part asks for a new token every time the
  old one is due to expire. With this method we don't need to save the
  users password. If we miss a refresh cycle (for example because the
  service was stopped) it will send the user an email to its notification
  address asking him to log in again to get a fresh token.
* **interface:** This provides a basic web interface to register new
  users, refresh logins or delete users.

All parts can run in one process or you can use separate processes for
each part. All they share is the configuration and the database.

## Configuration

The configuration can be done either by a ini-format configuration file
or via environment variables. The later is used for running the service
via docker. All config option have ro be below a section called `DEFAULT`.
You can just copy and modify the example config.

The following table describes all options:

|file-option  / env-var | type     | default    | description |
------------------------|----------|------------|----------|
|`WALLABAG_HOST`        | required |            | The http url of the Wallabag host. |
|`DB_URI`               | required |            | The dbapi url for the database. |
|`CLIENT_ID`            | required |            | The Wallabag client id. Read [here](https://doc.wallabag.org/en/developer/api/oauth.html) how to get it.    |
|`CLIENT_SECRET`        | required |            | The Wallabag client secret. Read above. |
|`DOMAIN`               | required |            | the domain the interface for the service is accessible on. |
|`SMTP_FROM`            | required |            | The from-address to use. |
|`SMTP_HOST`            | required |            | The SMTP hostname or ip. |
|`SMTP_PORT`            | required |            | The Port of the SMTP server. |
|`SMTP_USER`            | required |            | The user for SMTP auth. |
|`SMTP_PASSWD`          | required |            | The password for SMTP auth. |
|`SMTP_TLS`             | optional |  True      | Enable email encryption. Set to False or 0 to disable it.|
|`TAG`                  | optional | `kindle`   | The tag to consume. |
|`REFRESH_GRACE`        | optional | `120`      | The amount of seconds the token is refreshed before expiring. |
|`CONSUME_INTERVAL`     | optional | `30`       | The time in seconds between two consume cycles. |
|`INTERFACE_HOST`       | optional | `120.0.0.1`| The IP the user interface should bind to.  |
|`INTERFACE_PORT`       | optional | `8080`     | The port the user interface should bind. |

The configuration is read by default from the environment. But it could be read either from a `.ini` or `.env` file or from a path given to the commandline option `--cfg`.


## Running

Every component must be enabled via a commandline switch. To run all three
in one process use all three:
```
$ ./service.py --refresher --consumer --interface
```

For more information about commandline options use `--help`.


## Database

The service uses a database. The easiest option is to use sqlite. To save
all data in a file called database.db in the current working directory set
`sqlite:///database.db` in the config option `db_uri` or the env variable
`DB_URI`.

To initialize the database, run the server once with `--create_db`.


## Docker

The provided dockerfile makes it easy to use the software as a docker
container. The most recent version from the main branch is available through a
[automated build on ghcr.io](https://github.com/natilou/wallabag-kindle-consumer/pkgs/container/wallabag-kindle-consumer).

You can easily configure the container via the environment variables from
above. Just make sure, that the database is in a volume if you use sqlite.


## Usage

As soon as you've set it all up you can register your Wallabag user in the
Web-UI. The service does not store any login information other than the
user name and the API token for Wallabag. All actions that need a valid
user like register/login/delete a user are authenticated directly against
the Wallabag server.

## License

MIT

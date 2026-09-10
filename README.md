# Sender Policy Flattener

We had a problem in our organisation that caused our SPF records to become invalid:

When customers computers were querying our SPF records, there were more than 10 lookups required after following all of the `include:` remarks.

Solution? Query them ourselves, and create a much more condense list of SPF records.

## But wait... What if the downstream records change?

Part of what the script does is that it creates a JSON file that keeps track of the last list of IP Addresses that your combination of SPF records had.

When the hashsum of your IP Addresses changes, it will send out an email (or just dump HTML if it can't find an email server) with a handy diff & BIND format for viewing what has changed, and promptly updating it.

You could theoretically extract the flat IP records from the resulting JSON file and automatically update your DNS configuration with it.

## Installation

### Via git clone

Clone this repo and run

```shell
pip install poetry
poetry install
```

### Via pip

```shell
pip install sender_policy_flattener
```

## Usage

```shell
usage: spflat [-h] [-c CONFIG] [-r RESOLVERS] [-e MAILSERVER] [-t TOADDR]
              [-f FROMADDR] [-p PASSWORD] [-s SUBJECT] [-u UPDATE_SUBJECT]
              [-D SENDING_DOMAIN] [-d DOMAINS] [-o OUTPUT]
              [--update-records] [--force-update] [--no-email]

A script that crawls and compacts SPF records into IP networks. This helps to
avoid exceeding the DNS lookup limit of the Sender Policy Framework (SPF)
https://tools.ietf.org/html/rfc7208#section-4.6.4

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Name/path of JSON configuration file
  -r RESOLVERS, --resolvers RESOLVERS
                        Comma separated DNS servers to be used
  -e MAILSERVER, --mailserver MAILSERVER
                        Server to use for mailing alerts
  -t TOADDR, --to TOADDR
                        Recipient address for email alert
  -f FROMADDR, --from FROMADDR
                        Sending address for email alert
  -p PASSWORD, --pass PASSWORD
                        Password for sending address
  -s SUBJECT, --subject SUBJECT
                        Subject string, must contain {zone}
  -u UPDATE_SUBJECT, --update_subject UPDATE_SUBJECT
                        Update subject string, must contain {zone}
  -D SENDING_DOMAIN, --sending-domain SENDING_DOMAIN
                        The domain which emails are being sent from
  -d DOMAINS, --domains DOMAINS
                        Comma separated domain:rrtype to flatten to IP
                        addresses. Imagine these are your SPF include
                        statements.
  -o OUTPUT, --output OUTPUT
                        Name/path of output file
  --update-records      Update SPF records in CloudFlare
  --force-update        Force an update of SPF records in Cloudflare
  --no-email            don't send the email
```

Example

```shell
spflat --resolvers 8.8.8.8,8.8.4.4 \
    --to me@mydomain.com \
    --from admin@mydomain.com \
    --subject 'SPF for {zone} has changed!' \
    --domains gmail.com:txt,sendgrid.com:txt,yahoo.com:a \
    --sending-domain mydomain.com
```

or

```shell
spflat --config spf.json
```

You can specify a config file, or you can specify all of the optional arguments from the command line.

I've provided a `settings.json` file with an example configuration file.

## Supported Python versions

Python 3.12 is supported. See the latest test and container-build results in
[GitHub Actions](https://github.com/dismantl/sender_policy_flattener/actions).

## 3rd party dependencies

- netaddr
- dnspython

## Example email format

![example screenshot](https://raw.githubusercontent.com/cetanu/sender_policy_flattener/master/example/email_example.png)

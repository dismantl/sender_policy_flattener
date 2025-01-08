"""
A script that crawls and compacts SPF records into IP networks.
This helps to avoid exceeding the DNS lookup limit of the Sender Policy Framework (SPF)
https://tools.ietf.org/html/rfc7208#section-4.6.4
"""

import argparse
import json

import sender_policy_flattener


# noinspection PyMissingOrEmptyDocstring
def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Name/path of JSON configuration file",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-r",
        "--resolvers",
        dest="resolvers",
        help="Comma separated DNS servers to be used",
        default="8.8.8.8,8.8.4.4",
        required=False,
    )

    parser.add_argument(
        "-e",
        "--mailserver",
        dest="mailserver",
        help="Server to use for mailing alerts",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-t",
        "--to",
        dest="toaddr",
        help="Recipient address for email alert",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-f",
        "--from",
        dest="fromaddr",
        help="Sending address for email alert",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-p",
        "--pass",
        dest="password",
        help="Password for sending address",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-s",
        "--subject",
        dest="subject",
        help="Subject string, must contain {zone}",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-u",
        "--update_subject",
        dest="update_subject",
        help="Update subject string, must contain {zone}",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-D",
        "--sending-domain",
        dest="sending_domain",
        help="The domain which emails are being sent from",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-d",
        "--domains",
        dest="domains",
        help="Comma separated domain:rrtype to flatten to IP addresses. Imagine these are your SPF include statements.",
        default=None,
        required=False,
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        help="Name/path of output file",
        default="spf_sums.json",
        required=False,
    )

    parser.add_argument(
        "--update-records",
        dest="update",
        help="Update SPF records in CloudFlare",
        action="store_true",
        default=False,
        required=False,
    )

    parser.add_argument(
        "--force-update",
        help="Force an update of SPF records in Cloudflare",
        action="store_true",
        dest="force_update",
        default=False,
        required=False,
    )

    parser.add_argument(
        "--no-email",
        help="don't send the email",
        dest="sendemail",
        default=True,
        required=False,
        action="store_false",
    )

    arguments = parser.parse_args()

    if arguments.sending_domain:
        spf_includes = [x.split(":") for x in str(arguments.domains).split(",")]
        arguments.domains = {
            arguments.sending_domain: {d[0]: d[1] for d in spf_includes}
        }

    if arguments.config:
        with open(arguments.config) as config:
            settings = json.load(config)
            arguments.resolvers = settings["resolvers"]
            arguments.toaddr = settings["email"]["to"]
            arguments.fromaddr = settings["email"]["from"]
            arguments.password = settings["email"]["pass"]
            arguments.subject = settings["email"]["subject"]
            arguments.update_subject = settings["email"]["update_subject"]
            arguments.mailserver = settings["email"]["server"]
            arguments.domains = settings["sending domains"]
            arguments.output = settings["output"]

    if arguments.sendemail:
        required_non_config_args = all(
            [
                arguments.toaddr,
                arguments.fromaddr,
                arguments.password,
                arguments.subject,
                arguments.update_subject,
                arguments.mailserver,
                arguments.domains,
            ]
        )
    else:
        required_non_config_args = all([arguments.domains])

    if not required_non_config_args:
        parser.print_help()
        exit()

    if "{zone}" not in arguments.subject:
        raise ValueError("Subject must contain {zone}")

    return arguments


def main():
    args = parse_arguments()
    sender_policy_flattener.main(args)


if __name__ == "__main__":
    main()

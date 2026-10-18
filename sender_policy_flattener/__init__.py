# coding=utf-8
import json
import re
from dns.resolver import Resolver
from sender_policy_flattener.crawler import spf2ips
from sender_policy_flattener.formatting import sequence_hash
from sender_policy_flattener.email_utils import email_changes
from .cf_dns import TXTrec

if "FileNotFoundError" not in locals():
    FileNotFoundError = IOError


def update_spf_records(cfzone, domain, records):
    """Write the flattened chain; return True only if every record was written."""
    numrecs = len(records)
    all_updated = True
    print(f"\n**** Updating {numrecs} SPF Records for domain {domain}\n")
    for i in range(0, numrecs):
        recname = f"spf{i}.{domain}"
        print(f"===> Updating {recname} TXT record..", end="")
        if cfzone.update(recname, records[i], addok=True):
            print("..Successfully updated\n")
        else:
            all_updated = False
            print(
                f"Failed!\n\n********** WARNING: Update of {recname} TXT record Failed\n"
            )
    return all_updated


def delete_stale_spf_records(cfzone, domain, keep):
    """Delete spfN.<domain> SPF records with N >= keep.

    Records whose content is not an SPF policy are left alone, since the name
    alone does not prove spflat created them.
    """
    pattern = re.compile(rf"spf(\d+)\.{re.escape(domain)}\.?", re.IGNORECASE)
    stale = []
    for record in cfzone.all():
        match = pattern.fullmatch(record.name)
        if match and int(match.group(1)) >= keep:
            stale.append((int(match.group(1)), record))

    for _, record in sorted(stale, key=lambda item: item[0]):
        if not record.content.lstrip('"').lower().startswith("v=spf1"):
            print(
                f"===> Skipping {record.name} TXT record: content is not an SPF policy\n"
            )
            continue
        print(f"===> Deleting stale {record.name} TXT record..", end="")
        cfzone.zone.delete(record.id)
        print("..Successfully deleted\n")


def flatten(
    input_records,
    dns_servers,
    email_server,
    email_subject,
    update_subject,
    fromaddress,
    toaddress,
    password,
    update=False,
    email=True,
    lastresult=None,
    force_update=False,
):
    resolver = Resolver()
    # resolver.nameservers = dns_servers
    if dns_servers:
        resolver.nameservers = dns_servers

    if lastresult is None:
        lastresult = dict()

    current = dict()

    for domain, spf_targets in input_records.items():
        records = spf2ips(spf_targets, domain, resolver)
        hashsum = sequence_hash(records)
        current[domain] = {"records": records, "sum": hashsum}
        previous_result = lastresult.get(domain)
        mismatch = False
        if previous_result:
            previous_sum = previous_result["sum"]
            current_sum = current[domain]["sum"]
            mismatch = previous_sum != current_sum
            if mismatch:
                print(
                    f"\n***WARNING: SPF changes detected for sender domain {domain}\n"
                )
            else:
                print(f"\nNO SPF changes detected for sender domain {domain}\n")

            if mismatch and email:
                print(f"Sending mis-match details email for sender domain {domain}")
                if update or force_update:
                    thesubject = update_subject
                else:
                    thesubject = email_subject
                email_changes(
                    zone=domain,
                    prev_addrs=lastresult[domain]["records"],
                    curr_addrs=current[domain]["records"],
                    subject=thesubject,
                    server=email_server,
                    fromaddr=fromaddress,
                    password=password,
                    toaddr=toaddress,
                )

        if (update or force_update) and (previous_result or force_update):
            cfzone = TXTrec(domain)
            all_updated = True
            if mismatch or force_update:
                all_updated = update_spf_records(cfzone, domain, records)
            if not previous_result:
                # Without a baseline the length of the published chain is
                # unknown, so cleanup waits for a run that has one.
                print(f"Skipping stale SPF record cleanup for {domain}: no baseline\n")
            elif not all_updated:
                print(
                    f"Skipping stale SPF record cleanup for {domain} because an update failed\n"
                )
            else:
                keep = len(records)
                if mismatch or force_update:
                    # Resolvers may still cache the previous chain, whose last
                    # record includes the next spfN name. Deleting that name now
                    # would make SPF checks permerror until the cache expires, so
                    # records dropped by this run are removed on the next run.
                    keep = max(keep, len(previous_result["records"]))
                delete_stale_spf_records(cfzone, domain, keep)

    return current if update or force_update or len(lastresult) == 0 else lastresult


def main(args):
    previous_result = None
    try:
        with open(args.output) as prev_hashes:
            previous_result = json.load(prev_hashes)
    except FileNotFoundError as e:
        print(repr(e))
    except Exception as e:
        print(repr(e))
    finally:
        spf = flatten(
            input_records=args.domains,
            lastresult=previous_result,
            dns_servers=args.resolvers,
            email_server=args.mailserver,
            fromaddress=args.fromaddr,
            password=args.password,
            toaddress=args.toaddr,
            email_subject=args.subject,
            update_subject=args.update_subject,
            update=args.update,
            email=args.sendemail,
            force_update=args.force_update,
        )
        with open(args.output, "w+") as f:
            json.dump(spf, f, indent=4, sort_keys=True)

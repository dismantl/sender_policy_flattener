from types import SimpleNamespace
from unittest.mock import Mock, patch

from sender_policy_flattener import delete_stale_spf_records, flatten


def cf_record(name, content='"v=spf1 ip4:192.0.2.1 ~all"', record_id=None):
    return SimpleNamespace(id=record_id or name, name=name, content=content)


def txt_zone(*records):
    cfzone = Mock()
    cfzone.all.return_value = list(records)
    cfzone.update.return_value = "record-id"
    return cfzone


def deleted_ids(cfzone):
    return [c.args[0] for c in cfzone.zone.delete.call_args_list]


def test_cleanup_deletes_only_spf_records_beyond_the_chain():
    cfzone = txt_zone(
        cf_record("spf0.example.com"),
        cf_record("spf1.example.com"),
        cf_record("spf3.example.com"),
        cf_record("spf2.example.com"),
        cf_record("spf2.mail.example.com"),
        cf_record("spf10.example.com.evil"),
        cf_record("spf4.example.com", content='"google-site-verification=abc"'),
        cf_record("example.com", content='"v=spf1 include:spf0.example.com ~all"'),
    )

    delete_stale_spf_records(cfzone, "example.com", keep=2)

    assert deleted_ids(cfzone) == ["spf2.example.com", "spf3.example.com"]


def run_flatten(records, previous_records, *, update=True, force_update=False):
    current = {"records": records, "sum": "new"}
    lastresult = {"example.com": {"records": previous_records, "sum": "old"}}
    with (
        patch("sender_policy_flattener.spf2ips", return_value=records),
        patch(
            "sender_policy_flattener.sequence_hash",
            return_value=current["sum"],
        ),
    ):
        return flatten(
            input_records={"example.com": {"spf.example.net": "txt"}},
            dns_servers=None,
            email_server="unused",
            email_subject="unused",
            update_subject="unused",
            fromaddress="unused",
            toaddress="unused",
            password="unused",
            update=update,
            email=False,
            lastresult=lastresult,
            force_update=force_update,
        )


def stale_chain_zone():
    return txt_zone(*(cf_record(f"spf{i}.example.com") for i in range(4)))


def test_shrunk_chain_keeps_previously_published_records_until_next_run():
    cfzone = stale_chain_zone()
    with patch("sender_policy_flattener.TXTrec", return_value=cfzone):
        run_flatten(["a", "b"], previous_records=["a", "b", "c"])

    assert [c.args[0] for c in cfzone.update.call_args_list] == [
        "spf0.example.com",
        "spf1.example.com",
    ]
    assert deleted_ids(cfzone) == ["spf3.example.com"]


def test_unchanged_chain_removes_records_left_by_an_earlier_shrink():
    cfzone = stale_chain_zone()
    with (
        patch("sender_policy_flattener.TXTrec", return_value=cfzone),
        patch("sender_policy_flattener.sequence_hash", return_value="same"),
        patch("sender_policy_flattener.spf2ips", return_value=["a", "b"]),
    ):
        flatten(
            input_records={"example.com": {"spf.example.net": "txt"}},
            dns_servers=None,
            email_server="unused",
            email_subject="unused",
            update_subject="unused",
            fromaddress="unused",
            toaddress="unused",
            password="unused",
            update=True,
            email=False,
            lastresult={"example.com": {"records": ["a", "b"], "sum": "same"}},
        )

    cfzone.update.assert_not_called()
    assert deleted_ids(cfzone) == ["spf2.example.com", "spf3.example.com"]


def test_failed_update_skips_cleanup():
    cfzone = stale_chain_zone()
    cfzone.update.side_effect = ["record-id", None]
    with patch("sender_policy_flattener.TXTrec", return_value=cfzone):
        run_flatten(["a", "b"], previous_records=["a", "b"])

    cfzone.zone.delete.assert_not_called()


def test_report_only_mode_does_not_touch_cloudflare():
    with patch("sender_policy_flattener.TXTrec") as txtrec:
        run_flatten(["a", "b"], previous_records=["a", "b", "c"], update=False)

    txtrec.assert_not_called()


def test_forced_first_run_writes_records_but_defers_cleanup():
    cfzone = stale_chain_zone()
    with (
        patch("sender_policy_flattener.TXTrec", return_value=cfzone),
        patch("sender_policy_flattener.sequence_hash", return_value="new"),
        patch("sender_policy_flattener.spf2ips", return_value=["a", "b"]),
    ):
        flatten(
            input_records={"example.com": {"spf.example.net": "txt"}},
            dns_servers=None,
            email_server="unused",
            email_subject="unused",
            update_subject="unused",
            fromaddress="unused",
            toaddress="unused",
            password="unused",
            update=True,
            email=False,
            lastresult={},
            force_update=True,
        )

    assert cfzone.update.call_count == 2
    cfzone.zone.delete.assert_not_called()

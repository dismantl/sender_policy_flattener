from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from sender_policy_flattener.cf_dns import CFrec, CFzone


def cloudflare_client():
    client = Mock()
    client.zones.list.side_effect = [
        SimpleNamespace(result=[]),
        SimpleNamespace(
            result=[SimpleNamespace(id="zone-id", name="example.com")]
        ),
    ]
    return client


@patch("sender_policy_flattener.cf_dns.Cloudflare")
def test_zone_discovery_uses_the_closest_matching_parent(mock_cloudflare):
    client = cloudflare_client()
    mock_cloudflare.return_value = client

    zone = CFzone("mail.example.com")

    assert zone.zoneid == "zone-id"
    assert zone.zonename == "example.com"
    assert client.zones.list.call_args_list == [
        call(match="all", name="mail.example.com"),
        call(match="all", name="example.com"),
    ]


@patch("sender_policy_flattener.cf_dns.Cloudflare")
def test_zone_record_operations_use_the_dns_records_api(mock_cloudflare):
    client = cloudflare_client()
    client.dns.records.create.return_value = SimpleNamespace(id="created-id")
    client.dns.records.update.return_value = SimpleNamespace(id="updated-id")
    client.dns.records.delete.return_value = SimpleNamespace(id="deleted-id")
    mock_cloudflare.return_value = client
    zone = CFzone("mail.example.com")

    params = {
        "name": "spf0.example.com",
        "type": "TXT",
        "ttl": 1,
        "content": '"v=spf1 -all"',
    }

    assert zone.create(params) == "created-id"
    assert zone.set("record-id", params) == "updated-id"
    assert zone.delete("record-id") == "deleted-id"
    client.dns.records.create.assert_called_once_with(zone_id="zone-id", **params)
    client.dns.records.update.assert_called_once_with(
        dns_record_id="record-id", zone_id="zone-id", **params
    )
    client.dns.records.delete.assert_called_once_with(
        dns_record_id="record-id", zone_id="zone-id"
    )


def test_record_reads_and_creates_against_page_results():
    zone = Mock(zonename="example.com")
    zone.get.return_value = SimpleNamespace(
        result=[SimpleNamespace(content='"v=spf1 -all"')]
    )
    zone.create.return_value = "created-id"
    record = CFrec.__new__(CFrec)
    record.type = "TXT"
    record.ttl = 1
    record.zone = zone
    record.zonename = zone.zonename

    assert record.get("spf0") == '"v=spf1 -all"'
    assert record.add("spf1", '"v=spf1 -all"') == "created-id"
    zone.create.assert_called_once_with(
        {
            "name": "spf1.example.com",
            "type": "TXT",
            "ttl": 1,
            "content": '"v=spf1 -all"',
        }
    )

from pathlib import Path

from app.services.yaml_service import YamlService


def test_sample_summary_and_round_trip() -> None:
    raw = (Path(__file__).parent / "fixtures" / "FixCloud.sample.yaml").read_bytes()
    service = YamlService()
    document = service.load(raw)
    summary = service.summary(document)

    assert summary["sections"]["proxies"] == 1
    assert summary["sections"]["proxyGroups"] == 2
    assert summary["sections"]["proxyProviders"] == 1
    assert summary["sections"]["rules"] == 3
    assert summary["sections"]["ruleProviders"] == 1
    assert summary["proxyTypes"] == {"socks5": 1}
    assert summary["ruleTypes"]["RULE-SET"] == 1
    assert summary["unknownTopLevel"] == ["experimental"]

    candidate = service.dump_candidate(document)
    assert service.summary(service.load(candidate)) == summary


def test_mapping_reorder_keeps_provider_content() -> None:
    raw = b"""proxy-providers:
  First:
    type: http
    url: https://one.example/
  Second:
    type: http
    url: https://two.example/
rules: []
"""
    service = YamlService()
    document = service.load(raw)
    service.apply_operations(
        document,
        [
            {
                "op": "move",
                "path": ["proxy-providers"],
                "fromIndex": 1,
                "toIndex": 0,
            }
        ],
    )
    candidate = service.dump_candidate(document)
    assert candidate.index(b"  Second:") < candidate.index(b"  First:")
    assert b"https://one.example/" in candidate
    assert b"https://two.example/" in candidate


def test_full_diff_keeps_sensitive_values_for_private_confirmation() -> None:
    before = b"secret: old-secret\nurl: http://user:pass@nas/private?token=old\n"
    after = b"secret: new-secret\nurl: http://user:pass@nas/private?token=new\n"
    diff = YamlService().full_diff(before, after)["text"]

    assert "old-secret" in diff
    assert "new-secret" in diff
    assert "user:pass" in diff
    assert "token=new" in diff

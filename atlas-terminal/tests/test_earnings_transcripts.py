"""Tests for earnings transcript delta analysis."""

from datetime import date

from server.services.earnings_transcripts import Transcript, compute_delta, default_quarter_pair, tokenize_and_normalize


def test_default_quarter_pair_uses_completed_quarter() -> None:
    current, previous = default_quarter_pair(date(2026, 4, 21))

    assert current == (2026, 1)
    assert previous == (2025, 4)


def test_tokenize_and_normalize_removes_common_call_words() -> None:
    tokens = tokenize_and_normalize("Thank you operator. Sovereign AI demand was strong, strong, strong.")

    assert "thank" not in tokens
    assert "operator" not in tokens
    assert "sovereign" in tokens
    assert tokens.count("strong") == 3


def test_compute_delta_surfaces_new_removed_and_emphasis_phrases() -> None:
    previous = Transcript(
        ticker="NVDA",
        year=2025,
        quarter=4,
        content="inventory correction inventory correction gaming demand gaming demand data center",
    )
    current = Transcript(
        ticker="NVDA",
        year=2026,
        quarter=1,
        content="sovereign AI sovereign AI AI infrastructure AI infrastructure data center data center data center",
    )

    delta = compute_delta(current, previous)

    assert delta["available"] is True
    assert any(row["phrase"] == "sovereign ai" for row in delta["new_phrases"])
    assert any(row["phrase"] == "inventory correction" for row in delta["removed_phrases"])
    assert any(row["phrase"] == "data center" for row in delta["emphasis_shift"])

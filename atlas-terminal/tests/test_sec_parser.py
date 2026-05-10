from pathlib import Path

from server.services import sec_parser


def test_download_and_extract_all_items_with_form_falls_back_to_20f(monkeypatch) -> None:
    calls: list[str] = []
    saved_meta: dict[str, str] = {}

    class FakeDownloader:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def get(self, form_type: str, ticker: str, limit: int = 1, download_details: bool = True) -> None:
            calls.append(form_type)

    def fake_find_downloaded_filing_path(_download_root: Path, _ticker: str, form_type: str):
        if form_type == "20-F":
            return Path("/tmp/nio-20f")
        return None

    def fake_get_main_text(_filing_dir: Path) -> str:
        return "\n".join(
            [
                "Item 3.D Risk Factors",
                "Battery supply and geopolitical risks remain material.",
                "Item 5. Operating and Financial Review and Prospects",
                "Management discusses margin recovery and delivery outlook.",
                "Item 15. Controls and Procedures",
                "Disclosure controls were effective.",
                "Item 18. Financial Statements",
                "Consolidated financial statements follow.",
            ]
        )

    monkeypatch.setattr(sec_parser, "_get_edgar_downloader", lambda: FakeDownloader)
    monkeypatch.setattr(sec_parser, "find_downloaded_filing_path", fake_find_downloaded_filing_path)
    monkeypatch.setattr(sec_parser, "get_main_10k_text", fake_get_main_text)
    monkeypatch.setattr(sec_parser, "read_main_10k_html_raw", lambda _path: "<html><body>20-F filing</body></html>")
    monkeypatch.setattr(sec_parser, "_save_10k_to_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sec_parser, "save_10k_html_slice", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sec_parser, "prepare_native_html_fragment_from_10k_raw", lambda raw_html: raw_html)
    monkeypatch.setattr(
        sec_parser,
        "_save_filing_meta_to_cache",
        lambda _ticker, filing_form: saved_meta.update({"filing_form": filing_form}),
    )

    sections, filing_form = sec_parser.download_and_extract_all_items_with_form("NIO", "test@example.com")

    assert calls[:2] == ["10-K", "20-F"]
    assert filing_form == "20-F"
    assert saved_meta["filing_form"] == "20-F"
    assert "Battery supply" in sections["item1a"]
    assert "margin recovery" in sections["item7"]
    assert "financial statements" in sections["item8"].lower()

from trafficgen.urlmatch import (
    is_twitch_url,
    is_vimeo_url,
    is_youtube_url,
    registrable_domain,
    same_domain,
)


def test_is_youtube_url():
    assert is_youtube_url("https://www.youtube.com/watch?v=abc")
    assert is_youtube_url("https://youtu.be/abc")
    assert is_youtube_url("HTTPS://YOUTUBE.COM/WATCH?V=ABC")  # case-insensitive
    assert not is_youtube_url("https://www.youtube.com/")     # homepage, not a watch URL
    assert not is_youtube_url("https://vimeo.com/123")


def test_is_vimeo_url():
    assert is_vimeo_url("https://vimeo.com/12345")
    assert is_vimeo_url("https://player.vimeo.com/video/12345")
    assert not is_vimeo_url("https://notvimeo.com/12345")
    assert not is_vimeo_url("https://example.com/vimeo.com")


def test_is_twitch_url():
    assert is_twitch_url("https://www.twitch.tv/somestreamer")
    assert is_twitch_url("https://twitch.tv/x")
    assert not is_twitch_url("https://example.com/twitch.tv")


def test_registrable_domain():
    assert registrable_domain("https://www.example.com/a") == "example.com"
    assert registrable_domain("https://example.com") == "example.com"
    assert registrable_domain("https://a.b.example.co/x") == "example.co"


def test_same_domain():
    assert same_domain("https://www.example.com/a", "https://example.com/b")
    assert not same_domain("https://example.com", "https://example.org")
    assert not same_domain("not a url", "")

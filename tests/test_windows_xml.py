from notification_watcher.windows import parse_notification_xml


def test_parse_toast_xml_basic():
    payload = """
    <toast>
      <visual>
        <binding template="ToastGeneric">
          <text>Title</text>
          <text>Subtitle</text>
          <text>Body text</text>
        </binding>
      </visual>
    </toast>
    """
    parsed = parse_notification_xml(payload)
    assert parsed["title"] == "Title"
    assert parsed["subtitle"] == "Subtitle"
    assert parsed["body"] == "Body text"


def test_parse_toast_xml_two_texts():
    payload = "<toast><text>Only</text><text>Two</text></toast>"
    parsed = parse_notification_xml(payload)
    assert parsed["title"] == "Only"
    assert parsed["body"] == "Two"


def test_parse_toast_xml_empty():
    assert parse_notification_xml("") == {"title": "", "subtitle": "", "body": ""}
    assert parse_notification_xml("<bad") == {"title": "", "subtitle": "", "body": ""}

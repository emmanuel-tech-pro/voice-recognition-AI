from assistant.commands.parser import IntentName, Risk, parse


def test_open_known_app():
    intent = parse("Open Chrome")
    assert intent.name is IntentName.OPEN_APP
    assert intent.args["app"] == "chrome"


def test_open_app_alias():
    assert parse("open vs code").args["app"] == "vs code"


def test_open_website():
    intent = parse("Open Facebook")
    assert intent.name is IntentName.OPEN_SITE
    assert intent.args["site"] == "facebook"


def test_open_url():
    intent = parse("open https://example.com")
    assert intent.name is IntentName.OPEN_URL
    assert intent.args["url"] == "https://example.com"


def test_search():
    intent = parse("search for python dataclasses")
    assert intent.name is IntentName.SEARCH
    assert intent.args["query"] == "python dataclasses"


def test_type_preserves_original_casing():
    intent = parse("Type hello John")
    assert intent.name is IntentName.TYPE
    assert intent.args["text"] == "hello John"


def test_unknown_target():
    intent = parse("open blender")
    assert intent.name is IntentName.UNKNOWN
    assert intent.args["target"] == "blender"


def test_exit_and_help():
    assert parse("exit").name is IntentName.EXIT
    assert parse("help").name is IntentName.HELP


def test_dangerous_command_is_flagged():
    assert parse("delete my project folder").risk is Risk.DANGEROUS
    assert parse("open chrome").risk is Risk.SAFE

# python -m pytest addons/test/test-misra.py
import pytest
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import subprocess


class CapturingStdout(object):

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        self.captured = []
        return self

    def __exit__(self, *args):
        self.captured.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


class CapturingStderr(object):

    def __enter__(self):
        self._stderr = sys.stderr
        sys.stderr = self._stringio = StringIO()
        self.captured = []
        return self

    def __exit__(self, *args):
        self.captured.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stderr = self._stderr


TEST_SOURCE_FILES = ['./addons/test/misra-test.c']


def setup_module(module):
    for f in TEST_SOURCE_FILES:
        p = subprocess.Popen(["./cppcheck", "--dump", "--quiet", f])
        p.communicate()[0]
        if p.returncode != 0:
            raise OSError("cppcheck returns error code: %d" % p.returncode)
    subprocess.Popen(["sync"])


def teardown_module(module):
    for f in TEST_SOURCE_FILES:
        subprocess.Popen(["rm", "-f", f + ".dump"])


@pytest.fixture
def checker():
    from addons.misra import MisraChecker, MisraSettings, get_args
    args = get_args()
    settings = MisraSettings(args)
    return MisraChecker(settings)


def test_loadRuleTexts_structure(checker):
    checker.loadRuleTexts("./addons/test/assets/misra_rules_structure.txt")
    assert(checker.ruleTexts.get(101, None) is None)
    assert(checker.ruleTexts[102].text == "Rule text.")
    assert(checker.ruleTexts.get(103, None) is None)


def test_loadRuleTexts_empty_lines(checker):
    checker.loadRuleTexts("./addons/test/assets/misra_rules_empty_lines.txt")
    assert(len(checker.ruleTexts) == 3)
    assert(len(checker.ruleTexts[102].text) == len("Rule text."))


def test_loadRuleTexts_mutiple_lines(checker):
    checker.loadRuleTexts("./addons/test/assets/misra_rules_multiple_lines.txt")
    assert(checker.ruleTexts[101].text == "Multiple lines text.")
    assert(checker.ruleTexts[102].text == "Multiple lines text.")
    assert(checker.ruleTexts[103].text == "Multiple lines text.")
    assert(checker.ruleTexts[104].text == "Should")
    assert(checker.ruleTexts[105].text == "Should")
    assert(checker.ruleTexts[106].text == "Should")


def test_verifyRuleTexts(checker):
    checker.loadRuleTexts("./addons/test/assets/misra_rules_dummy.txt")
    with CapturingStdout() as output:
        checker.verifyRuleTexts()
    captured = ''.join(output.captured)
    assert("21.3" not in captured)
    assert("1.3" in captured)


def test_rules_misra_severity(checker):
    checker.loadRuleTexts("./addons/test/assets/misra_rules_dummy.txt")
    assert(checker.ruleTexts[1004].misra_severity == 'Mandatory')
    assert(checker.ruleTexts[401].misra_severity == 'Required')
    assert(checker.ruleTexts[1505].misra_severity == 'Advisory')
    assert(checker.ruleTexts[2104].misra_severity == '')


def test_rules_cppcheck_severity(checker):
    checker.loadRuleTexts("./addons/test/assets/misra_rules_dummy.txt")
    with CapturingStderr() as output:
        checker.parseDump("./addons/test/misra-test.c.dump")
    captured = ''.join(output.captured)
    assert("(error)" not in captured)
    assert("(warning)" not in captured)
    assert("(style)" in captured)

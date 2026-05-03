import pytest
from utils.llm import check_eligibility
from utils.translations import UI_TRANSLATIONS

def test_check_eligibility_underage():
    res = check_eligibility(17, True, True, False, "en")
    assert res["eligible"] == False
    assert any("age" in r.lower() for r in res["reasons"])

def test_check_eligibility_valid():
    res = check_eligibility(25, True, True, False, "en")
    assert res["eligible"] == True

def test_check_eligibility_not_citizen():
    res = check_eligibility(25, False, True, False, "en")
    assert res["eligible"] == False

def test_check_eligibility_disqualified():
    res = check_eligibility(30, True, True, True, "en")
    assert res["eligible"] == False

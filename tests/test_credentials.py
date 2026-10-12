"""Local API settings use fake credentials and never touch a real project file."""
import os
from types import MappingProxyType

import pytest

from dailyreport.credentials import ALLOWED_VARIABLES, api_environment


def local_settings(tmp_path, content):
    (tmp_path / '.env.local').write_text(content, encoding='utf-8')
    return tmp_path


def test_missing_file_returns_a_copy_of_the_supplied_environment(tmp_path):
    original = {'PATH': 'test-bin', 'TAVILY_API_KEY': 'fake-inherited'}
    result = api_environment(tmp_path, MappingProxyType(original))
    assert result == original
    assert result is not original
    result['PATH'] = 'changed'
    assert original['PATH'] == 'test-bin'


def test_default_environment_is_copied_and_never_modified(tmp_path, monkeypatch):
    monkeypatch.delenv('TAVILY_API_KEY', raising=False)
    local_settings(tmp_path, 'TAVILY_API_KEY=fake-local')
    before = dict(os.environ)
    result = api_environment(tmp_path)
    assert result['TAVILY_API_KEY'] == 'fake-local'
    assert dict(os.environ) == before


def test_all_supported_api_settings_can_be_loaded(tmp_path):
    expected = {key: 'fake-' + key.lower() for key in ALLOWED_VARIABLES}
    local_settings(tmp_path, '\n'.join(f'{key}={value}' for key, value in expected.items()))
    assert api_environment(tmp_path, {}) == expected


def test_blank_lines_comments_bom_and_whitespace_are_supported(tmp_path):
    local_settings(tmp_path, '\ufeff# private settings\n\n  # comment\n TAVILY_API_KEY = fake-local \n')
    assert api_environment(tmp_path, {}) == {'TAVILY_API_KEY': 'fake-local'}


def test_complete_quotes_equals_and_literal_characters_are_preserved(tmp_path):
    local_settings(tmp_path, 'TAVILY_API_KEY="fake=a=b"\n'
                   "TWITTERAPI_IO_KEY='fake#literal'\n"
                   'BRAVE_API_KEY=$FAKE_NO_EXPANSION\n')
    assert api_environment(tmp_path, {}) == {
        'TAVILY_API_KEY': 'fake=a=b', 'TWITTERAPI_IO_KEY': 'fake#literal',
        'BRAVE_API_KEY': '$FAKE_NO_EXPANSION',
    }


def test_existing_nonempty_environment_wins_and_empty_settings_are_missing(tmp_path):
    original = {'TAVILY_API_KEY': 'fake-inherited', 'BRAVE_API_KEY': '   ', 'GH_TOKEN': ''}
    local_settings(tmp_path, 'TAVILY_API_KEY=fake-local\nBRAVE_API_KEY=fake-default\n'
                   'GH_TOKEN=\nGITHUB_TOKEN="  "\nGETX_API_KEY=\n')
    result = api_environment(tmp_path, original)
    assert result == {'TAVILY_API_KEY': 'fake-inherited', 'BRAVE_API_KEY': 'fake-default', 'GH_TOKEN': ''}
    assert original['BRAVE_API_KEY'] == '   '


def test_unknown_variable_reports_only_name_and_line_number(tmp_path):
    local_settings(tmp_path, '# comment\nUNSUPPORTED_API=fake-sensitive-value')
    with pytest.raises(ValueError, match='Unknown API setting UNSUPPORTED_API at line 2') as caught:
        api_environment(tmp_path, {})
    assert 'fake-sensitive-value' not in str(caught.value)


def test_duplicate_is_rejected_even_if_first_value_is_empty_or_environment_wins(tmp_path):
    local_settings(tmp_path, 'TAVILY_API_KEY=\nTAVILY_API_KEY=fake-sensitive-value')
    with pytest.raises(ValueError, match='Duplicate API setting TAVILY_API_KEY at line 2') as caught:
        api_environment(tmp_path, {'TAVILY_API_KEY': 'fake-existing'})
    assert 'fake-sensitive-value' not in str(caught.value)


@pytest.mark.parametrize('value', ['"fake-unclosed', "'fake-unclosed\"", "fake-stray'", '"',
                                  '"fake" trailing "'])
def test_malformed_quotes_never_echo_values(tmp_path, value):
    local_settings(tmp_path, 'TAVILY_API_KEY=' + value)
    with pytest.raises(ValueError) as caught:
        api_environment(tmp_path, {})
    assert 'TAVILY_API_KEY at line 1' in str(caught.value)
    assert 'fake' not in str(caught.value)


@pytest.mark.parametrize('line', ['fake-sensitive-line', 'not valid=fake-sensitive-value', '=fake-sensitive-value'])
def test_malformed_assignments_never_echo_line_or_value(tmp_path, line):
    local_settings(tmp_path, line)
    with pytest.raises(ValueError) as caught:
        api_environment(tmp_path, {})
    assert 'at line 1' in str(caught.value)
    assert 'fake-sensitive' not in str(caught.value)


def test_only_env_local_is_read(tmp_path):
    (tmp_path / '.env').write_text('TAVILY_API_KEY=fake-other-file', encoding='utf-8')
    assert api_environment(tmp_path, {}) == {}


def test_decoding_error_is_safe_and_has_no_exception_context(tmp_path):
    (tmp_path / '.env.local').write_bytes(b'TAVILY_API_KEY=fake-sensitive-\xff')
    with pytest.raises(ValueError, match='Unable to read project API settings') as caught:
        api_environment(tmp_path, {})
    assert 'fake-sensitive' not in str(caught.value)
    assert caught.value.__suppress_context__ is True


def test_permission_error_is_safe_and_does_not_mutate_environment(tmp_path, monkeypatch):
    def denied(*_args, **_kwargs):
        raise PermissionError('fake-sensitive-filesystem-detail')

    monkeypatch.setattr(type(tmp_path), 'read_text', denied)
    original = {'PATH': 'fake-bin'}
    with pytest.raises(ValueError, match='Unable to read project API settings') as caught:
        api_environment(tmp_path, original)
    assert 'fake-sensitive' not in str(caught.value)
    assert caught.value.__suppress_context__ is True
    assert original == {'PATH': 'fake-bin'}

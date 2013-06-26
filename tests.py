import datetime
import pytz

from httpretty import HTTPretty, httprettified

from builtwith import (BuiltWithDomainInfo, BuiltWith, UnsupportedApiVersion,
                       ENDPOINTS_BY_API_VERSION, VERSION_EXCEPTION_TEMPLATE)


@httprettified
def test_lookup():
    API_VERSION_TESTED = 1

    bw = BuiltWith('key')
    HTTPretty.register_uri(HTTPretty.GET, ENDPOINTS_BY_API_VERSION[API_VERSION_TESTED], body='true')

    result = bw.lookup('example.com')

    qs = HTTPretty.last_request.querystring
    assert qs.get('KEY') == ['key']
    assert qs.get('LOOKUP') == ['example.com']
    assert result is True


@httprettified
def test_lookup_alternate_version():
    API_VERSION_TESTED = 2

    bw = BuiltWith('key', api_version=API_VERSION_TESTED)

    HTTPretty.register_uri(HTTPretty.GET, ENDPOINTS_BY_API_VERSION[API_VERSION_TESTED],
                           body='{"Paths": []}')
    HTTPretty.register_uri(HTTPretty.GET, ENDPOINTS_BY_API_VERSION[API_VERSION_TESTED],
                           body='{"TOPSITE": "2013-06-19", "FULL": "2013-05-30"}')

    result = bw.lookup('example.com')

    qs = HTTPretty.last_request.querystring
    assert qs.get('KEY') == ['key']
    assert qs.get('LOOKUP') == ['example.com']
    assert isinstance(result, BuiltWithDomainInfo)
    assert {'Paths': []} == result.api_response_json

@httprettified
def test_unsupported_version():
    UNSUPPORTED_API_VERSION = 3

    try:
        bw = BuiltWith('key', api_version=UNSUPPORTED_API_VERSION)
    except UnsupportedApiVersion as e:
        assert VERSION_EXCEPTION_TEMPLATE % (UNSUPPORTED_API_VERSION) == str(e)
        return

    raise RuntimeError("UnsupportedApiVersion exception not raised when it should have been.")


TEST_DATETIME_EARLIEST = datetime.datetime(2012, 9, 6, 23, 0, tzinfo=pytz.UTC)
TEST_DATETIME_EARLIEST_STRING = u'/Date(1346972400000)/'

TEST_DATE_MIDDLING = datetime.date(2012, 9, 13)

TEST_DATETIME_LATEST = datetime.datetime(2012, 9, 20, 23, 0, tzinfo=pytz.UTC)
TEST_DATETIME_LATEST_STRING = u'/Date(1348182000000)/'

TEST_RESPONSE_JSON = {
    u'Paths': [{u'Url': u'',
                u'Domain': u'example.com',
                u'SubDomain': u'',
                u'Technologies': [{u'Name': u'HTML5 DocType',
                                   u'FirstDetected': TEST_DATETIME_EARLIEST_STRING,
                                   u'Tag': u'docinfo',
                                   u'Link': u'http://dev.w3.org/html5/spec/syntax.html#the-doctype',
                                   u'LastDetected': TEST_DATETIME_EARLIEST_STRING,
                                   u'Description': u'The DOCTYPE is a required preamble for HTML5 websites.'},
                                  {u'Name': u'Javascript',
                                   u'FirstDetected': TEST_DATETIME_LATEST_STRING,
                                   u'Tag': u'docinfo',
                                   u'Link': u'http://en.wikipedia.org/wiki/JavaScript',
                                   u'LastDetected': TEST_DATETIME_LATEST_STRING,
                                   u'Description': u'JavaScript is a scripting language most often used for '
                                                    'client-side web development. Its proper name is ECMAScript, '
                                                    'though "JavaScript" is much more commonly used. The website '
                                                    'uses JavaScript.'}]},
               {u'Url': u'',
                u'Domain': u'example.com',
                u'SubDomain': u'test',
                u'Technologies': [{u'Name': u'HTML5 DocType',
                                   u'FirstDetected': TEST_DATETIME_EARLIEST_STRING,
                                   u'Tag': u'docinfo',
                                   u'Link': u'http://dev.w3.org/html5/spec/syntax.html#the-doctype',
                                   u'LastDetected': TEST_DATETIME_EARLIEST_STRING,
                                   u'Description': u'The DOCTYPE is a required preamble for HTML5 websites.'},
                                  {u'Name': u'Javascript',
                                   u'FirstDetected': TEST_DATETIME_LATEST_STRING,
                                   u'Tag': u'docinfo',
                                   u'Link': u'http://en.wikipedia.org/wiki/JavaScript',
                                   u'LastDetected': TEST_DATETIME_LATEST_STRING,
                                   u'Description': u'JavaScript is a scripting language most often used for '
                                                   'client-side web development. Its proper name is ECMAScript, '
                                                   'though "JavaScript" is much more commonly used. The website '
                                                   'uses JavaScript.'}]}]}


@httprettified
def test_domain_info_object():
    domain_info = BuiltWithDomainInfo(TEST_RESPONSE_JSON, TEST_DATE_MIDDLING)

    assert (sorted([(u'example.com', u'', u''), (u'example.com', u'test', u'')])
            == sorted(domain_info.available_urls()))

    url_technologies = domain_info.get_technologies_by_url(domain="example.com", subdomain="", path="")

    assert (sorted(["HTML5 DocType", "Javascript"])
            == sorted(url_technologies.list_technologies()))

    js_info = url_technologies.get_technology_info('Javascript')

    assert js_info['Name'] == "Javascript"
    assert js_info['LastDetected'] == TEST_DATETIME_LATEST
    assert js_info['CurrentlyLive'] == True

    html5_info = url_technologies.get_technology_info('HTML5 DocType')

    assert html5_info['Name'] == "HTML5 DocType"
    assert html5_info['LastDetected'] == TEST_DATETIME_EARLIEST
    assert html5_info['CurrentlyLive'] == False

import datetime
import pytz
import re
import requests


ENDPOINTS_BY_API_VERSION = {1: 'http://api.builtwith.com/v1/api.json',
                            2: 'http://api.builtwith.com/v2/api.json'}


VERSION_EXCEPTION_TEMPLATE = "Version %s"


class UnsupportedApiVersion(NotImplementedError):
    pass


def _convert_string_to_utc_datetime(datetime_string):
    return datetime.datetime.fromtimestamp(
        int(re.search("\d+", datetime_string).group(0)) / 1000, pytz.UTC)


def _convert_string_to_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%d").date()


class UrlTechnologiesSet(object):

    def __init__(self, technologies_list, last_full_builtwith_scan):
        DATETIME_INFORMATION_NAMES = ["FirstDetected", "LastDetected"]

        self._technologies_by_name = {}
        for technologies_dict in technologies_list:
            for name in DATETIME_INFORMATION_NAMES:
                technologies_dict[name] = _convert_string_to_utc_datetime(technologies_dict[name])

            # According to the team at BuiltWith, it's best to just use the last "FULL" scan
            # time in the CurrentlyLive determination since BuiltWith doesn't publish their
            # smaller "TOPSITE" list. Downside is that this client will say some technologies were
            # successfully detected on "TOPSITE" sites on the the last BuiltWith scan when that's
            # not in fact accurate.
            technologies_dict['CurrentlyLive'] = (
                last_full_builtwith_scan <= technologies_dict['LastDetected'].date())

            self._technologies_by_name[technologies_dict['Name']] = technologies_dict

    def __iter__(self):
        return iter(self._technologies_by_name.values())

    def get_technology_info(self, technology_name):
        return self._technologies_by_name.get(technology_name, None)

    def list_technologies(self):
        return self._technologies_by_name.keys()


class BuiltWithDomainInfo(object):

    def __init__(self, api_response_json, last_full_builtwith_scan):
        self.api_response_json = api_response_json
        self._technologies_by_url = {}
        for path_entry in api_response_json['Paths']:
            url_key = self.__get_url_key(
                path_entry['Domain'], path_entry.get('SubDomain', None), path_entry['Url'])
            self._technologies_by_url[
                url_key] = UrlTechnologiesSet(path_entry['Technologies'], last_full_builtwith_scan)

    def __iter__(self):
        return iter(self._technologies_by_url.values())

    @staticmethod
    def __get_url_key(domain, subdomain, path):
        return domain, subdomain, path

    def available_urls(self):
        return self._technologies_by_url.keys()

    def get_technologies_by_url(self, domain, subdomain, path):
        return self._technologies_by_url.get(self.__get_url_key(domain, subdomain, path), None)


class BuiltWith(object):
    """
    BuiltWith API version client.

    V1:

    >>> from builtwith import BuiltWith
    >>> bw = BuiltWith(YOUR_API_KEY)
    >>> bw.lookup(URL)

    V2:

    >>> from builtwith import BuiltWith
    >>> bw = BuiltWith(YOUR_API_KEY, api_version=2)
    >>> bw.lookup(URL)
    """

    def __init__(self, key, api_version=1):
        if api_version not in ENDPOINTS_BY_API_VERSION.keys():
            raise UnsupportedApiVersion(VERSION_EXCEPTION_TEMPLATE % (api_version))

        self.key = key
        self.api_version = api_version

    def lookup(self, domain):
        """
        Lookup BuiltWith results for the given domain.
        """
        if self.api_version == 2:
            last_updated_data = requests.get(ENDPOINTS_BY_API_VERSION[self.api_version] + "?UPDATE=1").json()
            last_full_builtwith_scan = _convert_string_to_date(last_updated_data['FULL'])

        params = {
            'KEY': self.key,
            'LOOKUP': domain,
        }

        response = requests.get(ENDPOINTS_BY_API_VERSION[self.api_version],
                                params=params)

        return BuiltWithDomainInfo(response.json(), last_full_builtwith_scan) if self.api_version == 2 else response.json()

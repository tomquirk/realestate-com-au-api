"""
Provides linkedin api-related code
"""
import random
import logging
from time import sleep
from urllib.parse import urlencode
import json
from fajita import Fajita
import realestate_com_au.settings as settings

from realestate_com_au.graphql import searchByQuery


logger = logging.getLogger(__name__)


class RealestateComAu(Fajita):
    """
    Class for accessing realestate.com.au API.
    """

    API_BASE_URL = "https://lexa.realestate.com.au/graphql"
    REQUEST_HEADERS = {
        "content-type": "application/json",
        "origin": "https://www.realestate.com.au",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    }

    def __init__(
        self, proxies={}, debug=False,
    ):
        Fajita.__init__(
            self,
            base_url=RealestateComAu.API_BASE_URL,
            headers=RealestateComAu.REQUEST_HEADERS,
            proxies=proxies,
            debug=debug,
            cookie_directory=settings.COOKIE_PATH,
        )
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logger

    def search(
        self,
        channel="buy",
        location=None,
        surrounding_suburbs=True,
        exclude_no_sale_price=False,
        furnished=False,
        pets_allowed=False,
        ex_under_contract=False,
    ):
        query_variables = {
            "channel": channel,
            "page": 1,
            "localities": [{"searchLocation": location}],
            "filters": {
                "surroundingSuburbs": surrounding_suburbs,
                "excludeNoSalePrice": exclude_no_sale_price,
                "ex-under-contract": ex_under_contract,
                "furnished": furnished,
                "petsAllowed": pets_allowed,
            },
        }

        payload = {
            "operationName": "searchByQuery",
            "variables": {
                "query": json.dumps(query_variables),
                "testListings": False,
                "nullifyOptionals": False,
            },
            "query": searchByQuery.QUERY,
        }

        res = self._post("", json=payload)
        data = res.json()
        exact_listings = (
            data.get("data", {})
            .get("buySearch", {})
            .get("results", {})
            .get("exact", {})
            .get("items", [])
        )
        results = data.get("data", {}).get("buySearch", {}).get("results", {})
        surrounding_listings = results.get("surrounding", {}).get("items", [])

        listings = exact_listings + surrounding_listings

        return [listing.get("listing", {}) for listing in listings]

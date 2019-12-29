"""
Provides linkedin api-related code
"""
import random
import logging
from time import sleep
from urllib.parse import urlencode
import json
import re
from fajita import Fajita

import realestate_com_au.settings as settings
from realestate_com_au.graphql import searchBuy, searchRent
from realestate_com_au.objects.listing import get_listing

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
    _MAX_SEARCH_PAGE_SIZE = 100  # TODO untested
    _DEFAULT_SEARCH_PAGE_SIZE = 25

    def __init__(
        self, proxies={}, debug=False,
    ):
        Fajita.__init__(
            self,
            base_url=self.API_BASE_URL,
            headers=self.REQUEST_HEADERS,
            proxies=proxies,
            debug=debug,
            cookie_directory=settings.COOKIE_PATH,
        )
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logger

    def search(
        self,
        limit=-1,
        channel="buy",
        locations=[],
        surrounding_suburbs=True,
        exclude_no_sale_price=False,
        furnished=False,
        pets_allowed=False,
        ex_under_contract=False,
    ):
        def get_query_variables(page=1):
            query_variables = {
                "channel": channel,
                "page": page,
                "pageSize": (
                    min(limit, self._MAX_SEARCH_PAGE_SIZE)
                    if limit
                    else self._DEFAULT_SEARCH_PAGE_SIZE
                ),
                "localities": [{"searchLocation": location} for location in locations],
                "filters": {
                    "surroundingSuburbs": surrounding_suburbs,
                    "excludeNoSalePrice": exclude_no_sale_price,
                    "ex-under-contract": ex_under_contract,
                    "furnished": furnished,
                    "petsAllowed": pets_allowed,
                },
            }
            return query_variables

        def get_payload(query_variables):
            payload = {
                "operationName": "searchByQuery",
                "variables": {
                    "query": json.dumps(query_variables),
                    "testListings": False,
                    "nullifyOptionals": False,
                },
                "query": (searchBuy.QUERY if channel == "buy" else searchRent.QUERY),
            }

            if channel == "rent":
                payload["variables"]["smartHide"] = False
                payload["variables"]["recentHides"] = []

            return payload

        def parse_items(res):
            data = res.json()
            exact_listings = (
                data.get("data", {})
                .get(f"{channel}Search", {})
                .get("results", {})
                .get("exact", {})
                .get("items", [])
            )
            results = data.get("data", {}).get("buySearch", {}).get("results", {})
            surrounding_listings = results.get("surrounding", {}).get("items", [])

            listings = [
                get_listing(listing.get("listing", {}))
                for listing in exact_listings + surrounding_listings
            ]

            return listings

        def get_current_page(**kwargs):
            current_query_variables = json.loads(kwargs["json"]["variables"]["query"])
            return current_query_variables["page"]

        def next_page(**kwargs):
            current_page = get_current_page(**kwargs)
            kwargs["json"] = get_payload(get_query_variables(current_page + 1))
            return kwargs

        def is_done(items, res, **kwargs):
            import ipdb

            ipdb.set_trace()
            items_count = len(items)
            if limit > -1:
                if items_count >= limit:
                    return True

            data = res.json()
            results = data.get("data", {}).get("buySearch", {}).get("results", {})
            total = results.get("totalResultsCount")

            if items_count >= total:
                return True

            pagination = results.get("pagination")

            # failsafe
            if not pagination.get("moreResultsAvailable"):
                return False

            return False

        listings = self._scroll(
            "",
            "POST",
            parse_items,
            next_page,
            is_done,
            json=get_payload(get_query_variables(1)),
        )

        return listings

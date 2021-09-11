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
from realestate_com_au.graphql import searchBuy, searchRent, searchSold
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
        min_price=0,
        max_price=-1,
        min_bedrooms=0,
        max_bedrooms=-1,
        property_types=[],  # "house", "unit apartment", "townhouse", "villa", "land", "acreage", "retire", "unitblock",
        min_bathrooms=0,
        min_carspaces=0,
        min_land_size=0,
        construction_status=None,  # NEW, ESTABLISHED
        keywords=[],
        exclude_keywords=[]
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
            if (max_price is not None and max_price > -1) or (
                max_price is not None and min_price > 0
            ):
                price_filter = {}
                if max_price > -1:
                    price_filter["maximum"] = str(max_price)
                if min_price > 0:
                    price_filter["minimum"] = str(min_price)
                query_variables["filters"]["priceRange"] = price_filter
            if (max_bedrooms is not None and max_bedrooms > -1) or (
                max_bedrooms is not None and min_bedrooms > 0
            ):
                beds_filter = {}
                if max_bedrooms > -1:
                    beds_filter["maximum"] = str(max_bedrooms)
                if min_bedrooms > 0:
                    beds_filter["minimum"] = str(min_bedrooms)
                query_variables["filters"]["bedroomsRange"] = beds_filter
            if property_types:
                query_variables["filters"]["propertyTypes"] = property_types
            if min_bathrooms is not None and min_bathrooms > 0:
                query_variables["filters"]["minimumBathroom"] = str(min_bathrooms)
            if min_carspaces is not None and min_carspaces > 0:
                query_variables["filters"]["minimumCars"] = str(min_carspaces)
            if min_land_size is not None and min_land_size > 0:
                query_variables["filters"]["landSize"] = {"minimum": str(min_land_size)}
            if construction_status:
                query_variables["filters"]["constructionStatus"] = construction_status
            if keywords:
                query_variables["filters"]["keywords"] = {"terms": keywords}
            return query_variables

        def get_query():
            if (channel == "buy"):
                return searchBuy.QUERY

            if (channel == "sold"):
                return searchSold.QUERY

            return searchRent.QUERY

        def get_payload(query_variables):
            payload = {
                "operationName": "searchByQuery",
                "variables": {
                    "query": json.dumps(query_variables),
                    "testListings": False,
                    "nullifyOptionals": False,
                },
                "query": get_query(),
            }

            if channel == "rent":
                payload["variables"]["smartHide"] = False
                payload["variables"]["recentHides"] = []

            return payload

        def parse_items(res):
            data = res.json()
            results = (
                data.get("data", {}).get(f"{channel}Search", {}).get("results", {})
            )

            exact_listings = (results.get("exact", {}) or {}).get("items", [])
            surrounding_listings = (results.get("surrounding", {}) or {}).get(
                "items", []
            )

            listings = [
                get_listing(listing.get("listing", {}) or {})
                for listing in exact_listings + surrounding_listings
            ]

            # filter listings that contain exclude_keywords
            if exclude_keywords:
                pattern = re.compile("|".join(exclude_keywords))
                listings = [
                    listing
                    for listing in listings
                    if not re.search(pattern, listing.description)
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
            if not items:
                return True
            items_count = len(items)
            if limit > -1:
                if items_count >= limit:
                    return True

            data = res.json()
            results = (
                data.get("data", {}).get(f"{channel}Search", {}).get("results", {})
            )

            # total = results.get("totalResultsCount")
            # if items_count >= total:
            #     return True

            pagination = results.get("pagination")
            if not pagination.get("moreResultsAvailable"):
                return True

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

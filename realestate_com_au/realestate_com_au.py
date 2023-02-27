"""
Provides realestate.com.au api-related code
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

common_user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; FSL 7.0.6.01001)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393",
]


class RealestateComAu(Fajita):
    """
    Class for accessing realestate.com.au API.
    """

    API_BASE_URL = "https://lexa.realestate.com.au/graphql"
    AGENT_CONTACT_BASE_URL = "https://agent-contact.realestate.com.au"
    REQUEST_HEADERS = {
        "content-type": "application/json",
        "origin": "https://www.realestate.com.au",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": random.choice(common_user_agents),
    }
    _MAX_SEARCH_PAGE_SIZE = 100  # TODO untested
    _DEFAULT_SEARCH_PAGE_SIZE = 25

    def __init__(
        self,
        proxies={},
        debug=False,
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
        start_page=1,
        sold_limit=-1,
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
        exclude_keywords=[],
        sort_type=None,
    ):
        def get_query_variables(page=start_page):
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
            if sort_type:
                query_variables["sort_type"]=sort_type
            return query_variables

        def get_query():
            if channel == "buy":
                return searchBuy.QUERY

            if channel == "sold":
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
                    if not re.search(pattern, str(listing.description))
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

            if limit > -1 and items_count >= limit:
                return True

            # Sold Listings Limit (Sold listings accumulate indefinetely. Enables data from X most recent sold listings only)
            if channel == "sold" and sold_limit > -1 and items_count >= sold_limit:
                return True

            data = res.json()
            results = (
                data.get("data", {}).get(f"{channel}Search", {}).get("results", {})
            )

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

    """
    Returns true if form was submitted successfully.
    """

    def contact_agent(
        self,
        listing_id,
        from_address,
        from_name,
        message,
        subject="",
        from_phone="",
    ):
        payload = {
            "lookingTo": subject,
            "name": from_name,
            "fromAddress": from_address,
            "fromPhone": from_phone,
            "message": message,
            "likeTo": [],
        }

        res = self._post(
            f"/contact-agent/listing/{listing_id}",
            base_url=self.AGENT_CONTACT_BASE_URL,
            json=payload,
        )

        error = res.status_code != 201
        if error:
            print("Error: ", res.text)

        return not error

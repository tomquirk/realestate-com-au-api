from dataclasses import dataclass, field
import re
from realestate_com_au.utils import delete_nulls


@dataclass
class Listing:
    id: str
    badge: str                                              #Captures Promotional text not held elsewhere, such as 'Under Contract'
    url: str
    suburb: str
    state: str
    postcode: str
    short_address: str
    full_address: str
    property_type: str
    price: int
    price_text: str                                         #Captures the original text, such as a price range or comment. This is lost when converting to Integer
    bedrooms: int
    bathrooms: int
    parking_spaces: int
    building_size: int
    building_size_unit: str
    land_size: int
    land_size_unit: str
    listing_company_id: str
    listing_company_name: str
    listing_company_phone: str
    auction_date: str
    available_date: str
    sold_date: str
    description: str
    images: list = field(default_factory=list)              #Captures Links to the photographic media
    images_floorplans: list = field(default_factory=list)   #Captures Links to the floorplans
    listers: list = field(default_factory=list)
    inspections: list = field(default_factory=list)         # Captures inspections


@dataclass
class Lister:
    id: str
    name: str
    agent_id: str
    job_title: str
    url: str
    phone: str
    email: str

@dataclass
class MediaItem:
    link: str

@dataclass
class Inspection:
    start_time: str
    end_time: str
    label: str
    label_short: str

def parse_availability(availability):
    if not availability:
        return None
    # Cut off the "Available" text from the front of the string so dates can be somewhat parsed
    return availability.replace("Available ", "")

def parse_price_text(price_display_text):
    regex = r".*\$([0-9\,\.]+(?:k|K|m|M)*).*"
    price_groups = re.search(regex, price_display_text)
    price_text = (
        price_groups.groups()[
            0] if price_groups and price_groups.groups() else None
    )
    if price_text is None:
        return None

    price = None
    if price_text[-1] == "k" or price_text[-1] == "K":
        price = float(price_text[:-1].replace(",", ""))

        price *= 1000
    elif price_text[-1] == "m" or price_text[-1] == "M":
        price = float(price_text[:-1].replace(",", ""))
        price *= 1000000
    else:
        price = float(price_text.replace(",", "").split('.')[0])

    return int(price)


def parse_phone(phone):
    if not phone:
        return None
    return phone.replace(" ", "")

def parse_description(description):
    if not description:
        return None
    # return description.replace("<br/>", "\n")
    return description

def get_lister(lister):
    lister = delete_nulls(lister)
    lister_id = lister.get("id")
    name = lister.get("name")
    agent_id = lister.get("agentId")
    job_title = lister.get("jobTitle")
    url = lister.get("_links", {}).get("canonical", {}).get("href")
    phone = parse_phone(lister.get("preferredPhoneNumber"))
    email = lister.get("email")  # TODO untested, need to confirm
    return Lister(
        id=lister_id,
        name=name,
        agent_id=agent_id,
        job_title=job_title,
        url=url,
        phone=phone,
        email=email,
    )

def get_image(media):
    """Creates an object representing an image from the listing. Replaces the {size} parameter with a known working varaible"""
    size_to_insert_into_link = '1144x888-format=webp'
    return MediaItem(
        link=media.get('templatedUrl',{}).replace("{size}", size_to_insert_into_link)
    )

def get_inspection(inspection):
    inspection = delete_nulls(inspection)
    start_time = inspection.get("startTime")
    end_time = inspection.get("endTime")
    label = inspection.get("display", []).get("longLabel")
    label_short = inspection.get("display", []).get("shortLabel")
    return Inspection(
        start_time=start_time,
        end_time=end_time,
        label=label,
        label_short=label_short
    )

def get_listing(listing):
    listing = delete_nulls(listing)
    # delete null keys for convenience

    property_id = listing.get("id")
    badge = listing.get("badge", {}).get("label")
    url = listing.get("_links", {}).get("canonical", {}).get("href")
    address = listing.get("address", {})
    suburb = address.get("suburb")
    state = address.get("state")
    postcode = address.get("postcode")
    short_address = address.get("display", {}).get("shortAddress")
    full_address = address.get("display", {}).get("fullAddress")
    property_type = listing.get("propertyType", {}).get("id")
    listing_company = listing.get("listingCompany", {})
    listing_company_id = listing_company.get("id")
    listing_company_name = listing_company.get("name")
    listing_company_phone = parse_phone(listing_company.get("businessPhone"))
    features = listing.get("generalFeatures", {})
    bedrooms = features.get("bedrooms", {}).get("value")
    bathrooms = features.get("bathrooms", {}).get("value")
    parking_spaces = features.get("parkingSpaces", {}).get("value")
    property_sizes = listing.get("propertySizes", {})
    building_size = property_sizes.get("building", {}).get("displayValue")
    building_size_unit = property_sizes.get(
        "building", {}).get("sizeUnit", {}).get("displayValue")
    land_size = float(''.join(property_sizes.get(
        "land", {}).get("displayValue", '-1').split(',')))
    land_size_unit = property_sizes.get("land", {}).get(
        "sizeUnit", {}).get("displayValue")
    price_text = listing.get("price", {}).get("display", "")
    price = parse_price_text(price_text)
    price_text = listing.get("price", {}).get("display")
    sold_date = listing.get("dateSold", {}).get("display")
    auction = listing.get("auction", {}) or {}
    auction_date = auction.get("dateTime", {}).get("value")
    available_date_text = listing.get("availableDate", {}).get("display")
    available_date = parse_availability(available_date_text)
    description = parse_description(listing.get("description"))
    images = [get_image(media) for media in listing.get("media", []).get('images',[])]
    images_floorplans = [get_image(media) for media in listing.get("media", []).get('floorplans',[])]
    listers = [get_lister(lister) for lister in listing.get("listers", [])]
    inspections = [get_inspection(inspection) for inspection in listing.get("inspections", [])]

    return Listing(
        id=property_id,
        badge=badge,
        url=url,
        suburb=suburb,
        state=state,
        postcode=postcode,
        short_address=short_address,
        full_address=full_address,
        property_type=property_type,
        listing_company_id=listing_company_id,
        listing_company_name=listing_company_name,
        listing_company_phone=listing_company_phone,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        parking_spaces=parking_spaces,
        building_size=building_size,
        building_size_unit=building_size_unit,
        land_size=land_size,
        land_size_unit=land_size_unit,
        price=price,
        price_text=price_text,
        auction_date=auction_date,
        available_date=available_date,
        sold_date=sold_date,
        description=description,
        images=images,
        images_floorplans=images_floorplans,
        listers=listers,
        inspections=inspections
    )

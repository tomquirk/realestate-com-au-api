# realestate-com-au-api

🏠Python wrapper for the realestate.com.au API

## Installation

Using **Python >= 3.6**:

```
$ pip install -e git+https://github.com/tomquirk/realestate-com-au-api.git
```

### Example usage

```python
from realestate_com_au import RealestateComAu

api = RealestateComAu()

# Get property listings
listings = api.search(location="seventeen seventy, qld 4677", channel="buy")
```

## Data classes

#### [Listing](/realestate_com_au/objects/listing.py#L6)

Data class for a listing. See [listing.py](/realestate_com_au/objects/listing.py#L6) for reference.

## Terms and Conditions

By using this project, you agree to the following Terms and Conditions:

### Usage

This project may not be used for any of the following:

- Commercial use
- Spam
- Storage of any Personally Identifiable Information
- Personal abuse (i.e. verbal abuse)

<a name="legal"></a>

## Legal

This code is in no way affiliated with, authorized, maintained, sponsored or endorsed by REA Group or any of its affiliates or subsidiaries. This is an independent and unofficial API. Use at your own risk.

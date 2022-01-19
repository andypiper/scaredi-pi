from datetime import datetime
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from requests import get
from waveshare_epd import epd1in54_V2 # Update this if needed for a different e-paper screen.

'''
Script to retrieve the number of confirmed Covid-19 cases in the past 7 day
in a local authority, normalise it for the local population, and
display the results on an e-ink screen.

LTLA_NAME = Lower Tier Local Authority (roughly, borough - not postcode area)
https://data.gov.uk/dataset/adb48074-34f0-4304-8dc4-e294240ad630/lower-tier-local-authority-to-upper-tier-local-authority-december-2018-lookup-in-england-and-wales-v2

LTLA_POPULATION = population estimate from Wikipedia via Google seach "<area> population mid 2019"
e.g. "Kingston upon Thames mid 2019" -> 177507 (est)

FONT_FILE should be in assets folder
'''

# Update these for your setup.

# LTLA_NAME = "Stroud"
# LTLA_POPULATION = 119019
# FONT_FILE = "Monoid-Regular.ttf"

LTLA_NAME = "Kingston upon Thames"
LTLA_POPULATION = 177507
FONT_FILE = "Roboto-Medium.ttf"

# Approximate multiplier between confirmed cases in past 7 days and
# actual prevalence in population, based on observing differences
# between ONS infection survey and Zoe estimates, and reported cases.

CASE_MULTIPLIER = 4

def get_cases():
    ENDPOINT = "https://api.coronavirus.data.gov.uk/v1/data"
    AREA_TYPE = "ltla"
    AREA_NAME = LTLA_NAME

    filters = [
        f"areaType={ AREA_TYPE }",
        f"areaName={ AREA_NAME }",
        f"date>2021-01-07"
    ]

    # Case numbers obtained from the newCasesBySpecimenDateRollingSum API field.
    # This is defined as:
    # Total number of people with at least one positive COVID-19 test result
    # (either lab-reported or lateral flow device) in the most recent 7-day period.
    structure = {
        "date": "date",
        "name": "areaName",
        "code": "areaCode",
        "newCasesBySpecimenDateRollingSum": "newCasesBySpecimenDateRollingSum"
    }
    api_params = {
        "filters": str.join(";", filters),
        "structure": json.dumps(structure, separators=(",", ":")),
        "format": "json"
    }

    try:
        response = get(ENDPOINT, params=api_params, timeout=10)
        if response.status_code >= 400:
            raise RuntimeError(f'Request failed: { response.text }')
        response = json.loads(response.content)
        cases = response['data'][0]['newCasesBySpecimenDateRollingSum']
        cases_per_1000 = (((cases * CASE_MULTIPLIER) / LTLA_POPULATION) * 1000.0)
    except Exception as e:
        print(e)
        cases_per_1000 = -1

    return cases_per_1000

dir_path = os.path.dirname(os.path.realpath(__file__))
assets_dir = '%s/../assets' % dir_path

def main():
    cases_per_1000 = get_cases()
    try:
        display = epd1in54_V2.EPD()
        display.init(0)
        display.Clear(255)

        w = display.height
        h = display.width
        
        # big/small sizes may need adjusting based on font face chosen
        bigfont = ImageFont.truetype(os.path.join(assets_dir, FONT_FILE), 80)
        smallfont = ImageFont.truetype(os.path.join(assets_dir, FONT_FILE), 16)

        image = Image.new(mode='1', size=(w, h), color=255)
        draw = ImageDraw.Draw(image)
        draw.text((0, 10), "%s" % LTLA_NAME,
              font=smallfont, fill=0, align='left') 
        draw.text((0, 30), "%.1f" % cases_per_1000,
              font=bigfont, fill=0, align='left')
        draw.text((0, 130), "COVID cases per 1000",
              font=smallfont, fill=0, align='left')
        now = datetime.now()
        draw.text((0, 160), "updated %s" % now.strftime('%d %b %H:%M'),
              font=smallfont, fill=0, align='left')
        display.display(display.getbuffer(image))

    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()

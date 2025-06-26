from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class Country(Enum):
    CYPRUS = "CYPRUS"
    FRANCE = "FRANCE"
    BELGIUM = "BELGIUM"
    SPAIN = "SPAIN"
    ENGLAND = "ENGLAND"
    GERMANY = "GERMANY"
    ITALY = "ITALY"
    UNITED_STATES = "UNITED_STATES"
    CANADA = "CANADA"
    AUSTRALIA = "AUSTRALIA"
    INDIA = "INDIA"
    CHINA = "CHINA"
    JAPAN = "JAPAN"
    BRAZIL = "BRAZIL"
    POLAND = "POLAND"
    NETHERLANDS = "NETHERLANDS"
    UKRAINE = "UKRAINE"
    SWITZERLAND = "SWITZERLAND"
    SWEDEN = "SWEDEN"
    ALBANIA = "ALBANIA"
    RUSSIA = "RUSSIA"
    UNITED_ARAB_EMIRATES = "UNITED_ARAB_EMIRATES"
    ANDORRA = "ANDORRA"
    AUSTRIA = "AUSTRIA"
    BELARUS = "BELARUS"
    BULGARIA = "BULGARIA"
    CROATIA = "CROATIA"
    CZECH_REPUBLIC = "CZECH_REPUBLIC"
    DENMARK = "DENMARK"
    ESTONIA = "ESTONIA"
    FINLAND = "FINLAND"
    GEORGIA = "GEORGIA"
    GREECE = "GREECE"
    HUNGARY = "HUNGARY"
    TURKEY = "TURKEY"
    ROMANIA = "ROMANIA"
    PORTUGAL = "PORTUGAL"
    NORWAY = "NORWAY"
    MOLDOVA = "MOLDOVA"
    LITHUANIA = "LITHUANIA"
    LUXEMBOURG = "LUXEMBOURG"
    SERBIA = "SERBIA"
    SLOVAKIA = "SLOVAKIA"
    BOSNIA_AND_HERZEGOVINA = "BOSNIA_AND_HERZEGOVINA"
    LATVIA = "LATVIA"
    LIECHTENSTEIN = "LIECHTENSTEIN"
    ISRAEL = "ISRAEL"
    KAZAKHSTAN = "KAZAKHSTAN"
    AZERBAIJAN = "AZERBAIJAN"
    UZBEKISTAN = "UZBEKISTAN"
    TAJIKISTAN = "TAJIKISTAN"



country_code_map = {
    "CYPRUS": "106774002",
    "FRANCE": "105015875",
    "BELGIUM": "100565514",
    "SPAIN": "105646813",
    "ENGLAND": "102299470",
    "GERMANY": "101282230",
    "ITALY": "103350119",
    "UNITED_STATES": "103644278",
    "UNITED STATES": "103644278",
    "CANADA": "101174742",
    "AUSTRALIA": "101452733",
    "INDIA": "102713980",
    "CHINA": "102890883",
    "JAPAN": "101355337",
    "BRAZIL": "106057199",
    "POLAND": "105072130",
    "NETHERLANDS": "102890719",
    "UKRAINE": "102264497",
    "SWITZERLAND": "106693272",
    "SWEDEN": "105117694",
    "ALBANIA": "102845717",
    "RUSSIA": "101728296",
    "UNITED_ARAB_EMIRATES": "104305776",
    "UNITED ARAB EMIRATES": "104305776",
    "ANDORRA": "106296266",
    "AUSTRIA": "103883259",
    "BELARUS": "101705918",
    "BULGARIA": "105333783",
    "CROATIA": "104688944",
    "CZECH_REPUBLIC": "104508036",
    "CZECH REPUBLIC": "104508036",
    "DENMARK": "104514075",
    "ESTONIA": "102974008",
    "FINLAND": "100456013",
    "GEORGIA": "106315325",
    "GREECE": "104677530",
    "HUNGARY": "100288700",
    "TURKEY": "106732692",
    "ROMANIA": "106670623",
    "PORTUGAL": "100364837",
    "NORWAY": "103819153",
    "MOLDOVA": "106178099",
    "LITHUANIA": "101464403",
    "LUXEMBOURG": "104042105",
    "SERBIA": "101855366",
    "SLOVAKIA": "103119917",
    "BOSNIA_AND_HERZEGOVINA": "102869081",
    "BOSNIA AND HERZEGOVINA": "102869081",
    "LATVIA": "104341318",
    "LIECHTENSTEIN": "100878084",
    "ISRAEL": "101620260",
    "KAZAKHSTAN": "106049128",
    "AZERBAIJAN": "103226548",
    "UZBEKISTAN": "107734735",
    "TAJIKISTAN": "105925962",
}

class KeywordResponse(BaseModel):
    keywords: List[str]
    locations: List[Country] = Field(
        description=(
            """Leave empty if the vacancy doesn’t name any country or location"""
        )
    )
    russian_speaking: bool = Field(
        description=(
            "Return True unless the vacancy explicitly requires non-Russian-speaking candidates."
        ),
        default=True,
    )
    explanation: str = Field(
        description=(
            "Explanation of how the keywords were extracted. "
            "Explanation of how the locations were extracted. "
            "This is useful for debugging and understanding the model's reasoning."
        )
    )

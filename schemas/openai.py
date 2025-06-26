from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class Country(Enum):
    FRANCE = "FRANCE"
    BELGIUM = "BELGIUM"
    SPAIN = "SPAIN"
    ENGLAND = "ENGLAND"
    GERMANY = "GERMANY"
    ITALY = "ITALY"
    UNITED_STATES = "UNITED STATES"
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
    UNITED_ARAB_EMIRATES = "UNITED ARAB EMIRATES"
    ANDORRA = "ANDORRA"
    AUSTRIA = "AUSTRIA"
    BELARUS = "BELARUS"
    BULGARIA = "BULGARIA"
    CROATIA = "CROATIA"
    CZECH_REPUBLIC = "CZECH REPUBLIC"
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
    BOSNIA_AND_HERZEGOVINA = "BOSNIA AND HERZEGOVINA"
    LATVIA = "LATVIA"
    LIECHTENSTEIN = "LIECHTENSTEIN"
    ISRAEL = "ISRAEL"
    KAZAKHSTAN = "KAZAKHSTAN"
    AZERBAIJAN = "AZERBAIJAN"
    UZBEKISTAN = "UZBEKISTAN"
    TAJIKISTAN = "TAJIKISTAN"


class KeywordResponse(BaseModel):
    keywords: List[str]
    locations: List[Country] = Field(
        description=(
            """Leave empty if the vacancy doesn’t name any country or location. Country name shall be written in CAPITAL letters. List of available country names:
    FRANCE
    BELGIUM
    SPAIN
    ENGLAND
    GERMANY
    ITALY
    UNITED STATES
    CANADA
    AUSTRALIA
    INDIA
    CHINA
    JAPAN
    BRAZIL
    POLAND
    NETHERLANDS
    UKRAINE
    SWITZERLAND
    SWEDEN
    ALBANIA
    RUSSIA
    UNITED ARAB EMIRATES
    ANDORRA
    AUSTRIA
    BELARUS
    BULGARIA
    CROATIA
    CZECH REPUBLIC
    DENMARK
    ESTONIA
    FINLAND
    GEORGIA
    GREECE
    HUNGARY
    TURKEY
    ROMANIA
    PORTUGAL
    NORWAY
    MOLDOVA
    LITHUANIA
    LUXEMBOURG
    SERBIA
    SLOVAKIA
    BOSNIA AND HERZEGOVINA
    LATVIA
    LIECHTENSTEIN
    ISRAEL
    KAZAKHSTAN
    AZERBAIJAN
    UZBEKISTAN
    TAJIKISTAN
            """
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

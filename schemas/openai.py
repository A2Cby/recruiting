from pydantic import BaseModel, Field
from typing import List

class KeywordResponse(BaseModel):
    keywords: List[str]
    locations: List[str] = Field(
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

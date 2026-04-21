from typing import Literal
from pydantic import BaseModel, computed_field


DrivingFrequency = Literal["rarely", "occasionally", "regularly"]
TravelDistance = Literal["local", "long-distance"]
DriverBand = Literal[
    "0_5",
    "6_10",
    "11_25",
    "26_50",
    "51_100",
    "101_250",
    "251_500",
    "501_1000",
    "1001_2000",
    "2001_plus",
]

DRIVER_BAND_VALUES = {
    "0_5": 3,
    "6_10": 8,
    "11_25": 18,
    "26_50": 38,
    "51_100": 75,
    "101_250": 175,
    "251_500": 375,
    "501_1000": 750,
    "1001_2000": 1500,
    "2001_plus": 2500,
}


class HNOAQuestionnaire(BaseModel):
    driver_band: DriverBand
    has_drivers_under_25: bool
    driving_frequency: DrivingFrequency
    travel_distance: TravelDistance
    has_driver_safety_measures: bool
    rents_vehicles: bool
    rental_vehicle_details: str | None = None
    has_high_value_vehicles: bool
    high_value_vehicle_details: str | None = None
    has_past_auto_incidents: bool
    past_auto_incident_details: str | None = None

    @computed_field
    @property
    def num_employees_driving(self) -> int:
        return DRIVER_BAND_VALUES.get(self.driver_band, 5)

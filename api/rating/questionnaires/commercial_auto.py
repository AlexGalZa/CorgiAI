from typing import Literal
from pydantic import BaseModel


BodyCategory = Literal["cars-pickup-suv", "trucks", "vans", "trailer", "other"]
VehicleRadius = Literal["0-50", "51-100", "201-499", "500-999", "1000-plus"]


class CommercialAutoQuestionnaire(BaseModel):
    vin: str
    body_category: BodyCategory
    year: int
    make: str
    model: str
    estimated_value: float
    vehicle_radius: VehicleRadius
    number_of_drivers: int

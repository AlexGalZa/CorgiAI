from typing import Optional
from pydantic import BaseModel


class KidnapRansomQuestionnaire(BaseModel):
    employees_travel_outside_us_canada: bool
    foreign_trips_planned: Optional[str] = None
    safety_procedures_changed_past_12mo: bool
    safety_procedures_explanation: Optional[str] = None
    safety_steps_for_international_travel: Optional[bool] = None
    safety_steps_travel_explanation: Optional[str] = None
    safety_steps_for_permanent_foreign_locations: bool
    safety_steps_foreign_explanation: Optional[str] = None
    permanent_foreign_locations: Optional[str] = None
    operates_ships_vessels: bool
    foodstuffs_beverages_pharmaceuticals: bool
    foodstuffs_explanation: Optional[str] = None

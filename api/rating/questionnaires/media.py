from typing import Literal
from pydantic import BaseModel, computed_field

MediaContentType = Literal["company-generated", "user-generated"]

ContentVolumeBand = Literal[
    "none",
    "under_100",
    "100_999",
    "1k_4999",
    "5k_19999",
    "20k_49999",
    "50k_plus",
]

VOLUME_BAND_VALUES: dict[str, int] = {
    "none": 0,
    "under_100": 50,
    "100_999": 500,
    "1k_4999": 2500,
    "5k_19999": 10000,
    "20k_49999": 30000,
    "50k_plus": 75000,
}


class MediaQuestionnaire(BaseModel):
    has_media_exposure: bool
    media_content_types: list[MediaContentType] | None = None
    original_content_volume: ContentVolumeBand | None = None
    ugc_content_volume: ContentVolumeBand | None = None
    has_content_moderation: bool
    moderation_details: str | None = None
    has_media_controls: bool
    has_past_complaints: bool
    past_complaint_details: str | None = None
    uses_third_party_content: bool
    has_licenses: bool | None = None

    @computed_field
    @property
    def company_content_volume(self) -> int:
        return (
            VOLUME_BAND_VALUES.get(self.original_content_volume, 0)
            if self.original_content_volume
            else 0
        )

    @computed_field
    @property
    def ugc_content_volume_numeric(self) -> int:
        return (
            VOLUME_BAND_VALUES.get(self.ugc_content_volume, 0)
            if self.ugc_content_volume
            else 0
        )

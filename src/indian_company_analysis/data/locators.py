"""Source-location contracts shared by extraction, normalization, and onboarding."""

from pydantic import Field

from indian_company_analysis.domain.models import DomainModel


class SourceFactLocator(DomainModel):
    """Location of one reported value or bounded excerpt within its original document."""

    page_number: int = Field(ge=1)
    table_id: str = Field(min_length=1)
    row_number: int = Field(ge=1)
    column_name: str = Field(min_length=1)
